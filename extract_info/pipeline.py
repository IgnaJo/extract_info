"""Pipeline de extracción de metadatos desde PDF."""

from __future__ import annotations

import logging
import re

from extract_info.extraction.anchors import (
    extract_value_after_anchor,
    find_value_near_label,
    find_values_block_near_label,
    search_in_pages,
)
from extract_info.extraction.patterns import (
    DocumentType,
    PAT_FECHA_VIGENTE,
    PAT_FECHA_VIGENTE_FALLBACK,
    PAT_FECHA_VIGENTE_NEXT_LINE,
    PAT_FECHA_VIGENTE_BEFORE,
    PAT_FECHA_NACIMIENTO,
    PAT_NOMBRE_CC,
    PAT_NOMBRE_NOT,
    PAT_NOMBRE_VARIANTS,
    PAT_PROTO_VALUE,
    PAT_REP_VALUE,
    PAT_FECHA_REP_VALUE,
    PAT_FECHA_FIRMA,
    PAT_RUT_CC,
    PAT_RUT_NOT,
    PAT_RUT_IN_NAME_BLOCK,
    PAT_RUT_VARIANTS,
    detect_document_type,
    normalizar_fecha,
)
from extract_info.extraction.text_reader import extract_full_text, get_page_count, open_pdf
from extract_info.extraction.validators import validate_campos
from extract_info.models import ContratoSchema, EstadoExtraccion

logger = logging.getLogger(__name__)

_SENTINEL_FECHA = "00-00-0000"
_SENTINEL_RUT = "0.000.000-0"


def _extract_fields_credit_card(pages, page_count) -> dict:
    """Extrae campos de contrato de tarjeta de crédito."""
    first_page_text = pages[0].full_text if pages else ""
    first_page_blocks = pages[0].blocks if pages else []

    # Use horizontal neighbor search for Nombre Completo (left column label at x≈56)
    nombre, nombre_block = find_value_near_label(
        first_page_blocks,
        PAT_NOMBRE_CC,
        search_horizontal=True,
    )
    # Clean nombre: if it contains newlines, take only first line
    if nombre and "\n" in nombre:
        nombre = nombre.split("\n")[0].strip()
    # RUT: try multiple strategies
    rut = None
    # Strategy 1: RUT in the same name block (combined name+RUT layout)
    if nombre_block:
        match = PAT_RUT_IN_NAME_BLOCK.search(nombre_block.text)
        if match:
            rut = match.group(1)
    # Strategy 2: RUT as horizontal neighbor of "RUT:" label (separate blocks layout)
    if not rut:
        # Use a simple label-only pattern for RUT (no value expected on same line)
        pat_rut_label = re.compile(r'^Rut\s*:', re.IGNORECASE)
        rut_val, rut_block = find_value_near_label(
            first_page_blocks,
            pat_rut_label,
            search_horizontal=True,
        )
        if rut_val:
            rut = rut_val.split("\n")[0].strip()
    # Format raw RUT if needed (no dots/dash)
    if rut and '-' not in rut and '.' not in rut and len(rut) >= 5:
        raw = rut.rstrip('kK')
        has_k = rut.upper().endswith('K')
        raw_len = len(raw)
        if raw_len == 8:
            # 7-digit RUT: X.XXX.XXX + check digit
            formatted = raw[0] + '.' + raw[1:4] + '.' + raw[4:7]
            check_input = int(raw[:7])
        elif raw_len == 9:
            # 8-digit RUT: XX.XXX.XXX + check digit
            formatted = raw[:2] + '.' + raw[2:5] + '.' + raw[5:8]
            check_input = int(raw[:8])
        else:
            formatted = None
        if formatted:
            total = 0
            multiplier = 2
            temp = check_input
            while temp > 0:
                total += (temp % 10) * multiplier
                temp //= 10
                multiplier = multiplier + 1 if multiplier < 7 else 2
            remainder = 11 - (total % 11)
            if remainder == 11:
                verif = '0'
            elif remainder == 10:
                verif = 'K'
            else:
                verif = str(remainder)
            rut = formatted + '-' + verif
    # Strategy 3: RUT without dash (raw digits like "254398470") - text search fallback
    if not rut and nombre_block:
        raw_match = re.search(r'(?:Rut|RUT)\s*[:\s]+\s*(\d{5,9}[kK]?)', first_page_text, re.IGNORECASE)
        if raw_match:
            rut_val = raw_match.group(1)
            if '-' not in rut_val and '.' not in rut_val:
                raw = rut_val.rstrip('kK')
                raw_len = len(raw)
                if raw_len == 8:
                    formatted = raw[0] + '.' + raw[1:4] + '.' + raw[4:7]
                    check_input = int(raw[:7])
                elif raw_len == 9:
                    formatted = raw[:2] + '.' + raw[2:5] + '.' + raw[5:8]
                    check_input = int(raw[:8])
                else:
                    formatted = None
                if formatted:
                    total = 0
                    multiplier = 2
                    temp = check_input
                    while temp > 0:
                        total += (temp % 10) * multiplier
                        temp //= 10
                        multiplier = multiplier + 1 if multiplier < 7 else 2
                    remainder = 11 - (total % 11)
                    if remainder == 11:
                        verif = '0'
                    elif remainder == 10:
                        verif = 'K'
                    else:
                        verif = str(remainder)
                    rut = formatted + '-' + verif
                else:
                    rut = rut_val
            else:
                rut = rut_val

    # Fecha contrato: "Vigentes al" on page 0 (always present). Fallback: search all pages.
    fecha_match = PAT_FECHA_VIGENTE.search(first_page_text)
    if not fecha_match:
        fecha_match = PAT_FECHA_VIGENTE_FALLBACK.search(first_page_text)
    if not fecha_match:
        fecha_match = PAT_FECHA_VIGENTE_NEXT_LINE.search(first_page_text)
    if not fecha_match:
        fecha_match = PAT_FECHA_VIGENTE_BEFORE.search(first_page_text)
    if not fecha_match:
        for page in pages:
            match = PAT_FECHA_VIGENTE.search(page.full_text)
            if not match:
                match = PAT_FECHA_VIGENTE_FALLBACK.search(page.full_text)
            if not match:
                match = PAT_FECHA_VIGENTE_NEXT_LINE.search(page.full_text)
            if not match:
                match = PAT_FECHA_VIGENTE_BEFORE.search(page.full_text)
            if match:
                fecha_match = match
                break
    # Pattern has multiple groups; extract the first non-None date
    if fecha_match:
        fecha_contrato = normalizar_fecha(fecha_match.group(1) or fecha_match.group(2) or fecha_match.group(3))
    else:
        fecha_contrato = None

    # Birth date from "Fecha Nacimiento:" (separate field, not used for contrato)
    nacimiento_match = PAT_FECHA_NACIMIENTO.search(first_page_text)
    fecha_nacimiento = normalizar_fecha(nacimiento_match.group(1)) if nacimiento_match else None

    proto, repertorio, fecha_repertorio = None, None, None

    values = find_values_block_near_label(
        first_page_blocks,
        re.compile(r"PROTOCOLIZADO"),
        num_values=3,
        max_vertical_dist=80.0,
    )

    if values and len(values) >= 3:
        proto = values[0]
        repertorio = values[1]
        fecha_repertorio = normalizar_fecha(values[2]) if PAT_FECHA_REP_VALUE.match(values[2]) else None
    elif values and len(values) == 2:
        proto = values[0]
        repertorio = values[1]

    if not proto:
        proto, _ = find_value_near_label(
            first_page_blocks,
            re.compile(r"PROTOCOLIZADO"),
            PAT_PROTO_VALUE,
            search_horizontal=True,
        )

    if not repertorio:
        repertorio, _ = find_value_near_label(
            first_page_blocks,
            re.compile(r"REP\s+N[°º]"),
            PAT_REP_VALUE,
            search_horizontal=True,
        )

    return {
        "nombre_completo": nombre,
        "rut": rut,
        "fecha_contrato": fecha_contrato,
        "fecha_nacimiento": fecha_nacimiento,
        "proto": proto,
        "repertorio": repertorio,
        "fecha_repertorio": fecha_repertorio,
        "cantidad_hojas": page_count,
    }


def _extract_fields_notarized(pages, page_count) -> dict:
    """Extrae campos de documento notariado."""
    last_pages = [page_count - 2, page_count - 1] if page_count >= 2 else [0]
    search_pages = last_pages + [0]

    first_page_blocks = pages[0].blocks if pages else []

    nombre = None
    rut = None
    fecha_firma = None

    result_nombre = search_in_pages(pages, PAT_NOMBRE_NOT, search_pages)
    if result_nombre:
        nombre = result_nombre[0]

    result_rut = search_in_pages(pages, PAT_RUT_NOT, search_pages)
    if result_rut:
        rut = result_rut[0]

    result_fecha = search_in_pages(pages, PAT_FECHA_FIRMA, search_pages)
    if result_fecha:
        fecha_firma = normalizar_fecha(result_fecha[0])

    proto = extract_value_after_anchor(first_page_blocks, re.compile(r"PROTOCOLIZADO\s+N[°º]?\s*(\d+)"))
    repertorio = extract_value_after_anchor(first_page_blocks, re.compile(r"(?:\*\*)?REP\s+N[°º]?\s*(\d+)"))

    fecha_repertorio = None
    if repertorio:
        match = re.search(rf"REP\s+N[°º]?\s*{re.escape(repertorio)}.*?DE\s*(\d{{2}}[-/]\d{{2}}[-/]\d{{4}})", pages[0].full_text if pages else "", re.IGNORECASE)
        if match:
            fecha_repertorio = normalizar_fecha(match.group(1))

    return {
        "nombre_completo": nombre,
        "rut": rut,
        "fecha_contrato": fecha_firma,
        "proto": proto,
        "repertorio": repertorio,
        "fecha_repertorio": fecha_repertorio,
        "cantidad_hojas": page_count,
    }


def _extract_fields(pdf_path: str) -> tuple[dict, DocumentType]:
    """Extrae campos crudos del PDF y detecta tipo de documento."""
    doc = open_pdf(pdf_path)
    try:
        pages = extract_full_text(doc)
        page_count = get_page_count(doc)

        if not pages:
            return {
                "nombre_completo": None,
                "rut": None,
                "fecha_contrato": None,
                "proto": None,
                "repertorio": None,
                "fecha_repertorio": None,
                "cantidad_hojas": page_count,
            }, DocumentType.CREDIT_CARD

        first_page_text = pages[0].full_text
        doc_type = detect_document_type(first_page_text)

        if doc_type == DocumentType.CREDIT_CARD:
            campos = _extract_fields_credit_card(pages, page_count)
        else:
            campos = _extract_fields_notarized(pages, page_count)

        return campos, doc_type
    finally:
        doc.close()


def process_pdf(pdf_path: str, nombre_carpeta: str) -> ContratoSchema:
    """Procesa un PDF y retorna un ContratoSchema validado."""
    nombre_archivo = pdf_path.rsplit("/", 1)[-1]

    try:
        campos, doc_type = _extract_fields(pdf_path)
    except Exception as e:
        logger.error("Error procesando %s: %s", pdf_path, e)
        return ContratoSchema(
            nombre_completo="ERROR",
            rut=_SENTINEL_RUT,
            fecha_contrato=_SENTINEL_FECHA,
            proto=1,
            repertorio=1,
            fecha_repertorio=_SENTINEL_FECHA,
            nombre_archivo=nombre_archivo,
            cantidad_hojas=1,
            nombre_carpeta=nombre_carpeta,
            estado_extraccion=EstadoExtraccion.ERROR,
            observaciones=str(e),
        )

    estado, observaciones = validate_campos(campos)

    return ContratoSchema(
        nombre_completo=campos["nombre_completo"] or "NO_EXTRAIDO",
        rut=campos["rut"] or _SENTINEL_RUT,
        fecha_contrato=campos["fecha_contrato"] or _SENTINEL_FECHA,
        proto=int(campos["proto"]) if campos["proto"] and campos["proto"].isdigit() else 1,
        repertorio=int(campos["repertorio"]) if campos["repertorio"] and campos["repertorio"].isdigit() else 1,
        fecha_repertorio=campos["fecha_repertorio"] or _SENTINEL_FECHA,
        nombre_archivo=nombre_archivo,
        cantidad_hojas=campos["cantidad_hojas"] or 1,
        nombre_carpeta=nombre_carpeta,
        estado_extraccion=estado,
        observaciones=observaciones,
    )
