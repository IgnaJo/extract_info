"""Pipeline de extracción de metadatos desde PDF."""

from __future__ import annotations

import logging
import os
import re

from extract_info.extraction.anchors import (
    find_value_near_label,
)
from extract_info.extraction.patterns import (
    PAT_FECHA_FIRMA,
    PAT_FECHA_REP_VALUE,
    PAT_FECHA_VIGENTE,
    PAT_FECHA_VIGENTE_BEFORE,
    PAT_FECHA_VIGENTE_FALLBACK,
    PAT_FECHA_VIGENTE_NEXT_LINE,
    PAT_NOMBRE_CC,
    PAT_NOMBRE_NOT,
    PAT_PROTO_VALUE,
    PAT_REP_VALUE,
    PAT_RUT_IN_NAME_BLOCK,
    PAT_RUT_NOT,
    detect_document_type,
)
from extract_info.extraction.text_reader import extract_full_text, get_page_count, open_pdf
from extract_info.extraction.validators import validate_campos
from extract_info.models import ContratoSchema, EstadoExtraccion

logger = logging.getLogger(__name__)

def _format_rut(raw: str) -> str | None:
    """Formatea RUT crudo (solo dígitos) a formato X.XXX.XXX-X con dígito verificador.
    Returns None si el formato no es válido.
    """
    raw_len = len(raw)
    if raw_len == 8:
        formatted = raw[0] + '.' + raw[1:4] + '.' + raw[4:7]
        check_input = int(raw[:7])
    elif raw_len == 9:
        formatted = raw[:2] + '.' + raw[2:5] + '.' + raw[5:8]
        check_input = int(raw[:8])
    else:
        return None
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
    return formatted + '-' + verif


# --- Inlined from extraction.anchors (single-use) ---

def _extract_value_after_anchor(
    blocks: list, anchor_pattern: re.Pattern, value_group: int = 1
) -> str | None:
    """Extrae el valor adyacente a un anclaje (legacy, mantener compatibilidad)."""
    for block in blocks:
        match = anchor_pattern.search(block.text)
        if match:
            break
    else:
        return None

    if match.lastindex and match.lastindex >= value_group:
        value = match.group(value_group)
        if value and value.strip():
            return value.strip()

    match_end = match.end()
    remaining = block.text[match_end:].strip()
    if remaining:
        return remaining.split("\n")[0].strip()

    try:
        idx = blocks.index(block)
    except ValueError:
        return None
    if idx + 1 < len(blocks):
        next_block = blocks[idx + 1]
        if next_block.top - block.bottom < 30:
            return next_block.text.strip()
    return None


def _parse_values_block(text: str, expected_count: int) -> list[str]:
    """Parsea un bloque de texto con múltiples valores separados por espacios/newlines."""
    parts = re.split(r"\s{2,}|\n", text)
    values = [p.strip() for p in parts if p.strip()]

    if len(values) >= expected_count:
        return values[:expected_count]

    return values if values else []


def _find_values_block_near_label(
    blocks: list, label_pattern: re.Pattern, num_values: int = 3, max_vertical_dist: float = 80.0
) -> list[str] | None:
    """Busca un bloque de valores múltiples cercano a un label."""
    label_block = None
    for block in blocks:
        if label_pattern.search(block.text):
            label_block = block
            break

    if label_block is None:
        return None

    label_center_y = (label_block.top + label_block.bottom) / 2
    label_x = label_block.left

    candidates = []
    for block in blocks:
        if block is label_block:
            continue

        block_center_y = (block.top + block.bottom) / 2
        vert_dist = abs(block_center_y - label_center_y)

        if vert_dist > max_vertical_dist:
            continue

        horiz_close = block.left >= label_x - 50
        if horiz_close:
            candidates.append((vert_dist, block))

    candidates.sort(key=lambda c: c[0])

    for _dist, candidate_block in candidates:
        text = candidate_block.text.strip()
        if text:
            return _parse_values_block(text, num_values)

    return None


def _search_in_pages(
    pages: list, anchor_pattern: re.Pattern, page_indices: list[int] | None = None
) -> tuple[str, int] | None:
    """Busca un anclaje en múltiples páginas. Retorna (valor, página)."""
    indices = page_indices if page_indices is not None else range(len(pages))
    for idx in indices:
        if idx >= len(pages):
            continue
        page = pages[idx]
        value = _extract_value_after_anchor(page.blocks, anchor_pattern)
        if value:
            return value, page.page_number
    return None


# --- End inlined helpers ---


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
        formatted = _format_rut(raw)
        if formatted:
            rut = formatted
    # Strategy 3: RUT without dash (raw digits like "254398470") - text search fallback
    if not rut and nombre_block:
        raw_match = re.search(
            r"(?:Rut|RUT)\s*[:\s]+\s*(\d{5,9}[kK]?)",
            first_page_text,
            re.IGNORECASE,
        )
        if raw_match:
            rut_val = raw_match.group(1)
            if '-' not in rut_val and '.' not in rut_val:
                raw = rut_val.rstrip('kK')
                formatted = _format_rut(raw)
                if formatted:
                    rut = formatted
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
        fecha_contrato = (
            fecha_match.group(1) or fecha_match.group(2) or fecha_match.group(3)
        ).replace("/", "-")
    else:
        fecha_contrato = None

    proto, repertorio, fecha_repertorio = None, None, None

    values = _find_values_block_near_label(
        first_page_blocks,
        re.compile(r"PROTOCOLIZADO"),
        num_values=3,
        max_vertical_dist=80.0,
    )

    if values and len(values) >= 3:
        proto = values[0]
        repertorio = values[1]
        fecha_repertorio = (
            values[2].replace("/", "-")
            if PAT_FECHA_REP_VALUE.match(values[2])
            else None
        )
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

    result_nombre = _search_in_pages(pages, PAT_NOMBRE_NOT, search_pages)
    if result_nombre:
        nombre = result_nombre[0]

    result_rut = _search_in_pages(pages, PAT_RUT_NOT, search_pages)
    if result_rut:
        rut = result_rut[0]

    result_fecha = _search_in_pages(pages, PAT_FECHA_FIRMA, search_pages)
    if result_fecha:
        fecha_firma = result_fecha[0].replace("/", "-")

    proto = _extract_value_after_anchor(
        first_page_blocks, re.compile(r"PROTOCOLIZADO\s+N[°º]?\s*(\d+)")
    )
    repertorio = _extract_value_after_anchor(
        first_page_blocks, re.compile(r"(?:\*\*)?REP\s+N[°º]?\s*(\d+)")
    )

    fecha_repertorio = None
    if repertorio:
        pattern = (
            rf"REP\s+N[°º]?\s*{re.escape(repertorio)}"
            r".*?DE\s*(\d{{2}}[-/]\d{{2}}[-/]\d{{4}})"
        )
        page_text = pages[0].full_text if pages else ""
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            fecha_repertorio = match.group(1).replace("/", "-")

    return {
        "nombre_completo": nombre,
        "rut": rut,
        "fecha_contrato": fecha_firma,
        "proto": proto,
        "repertorio": repertorio,
        "fecha_repertorio": fecha_repertorio,
        "cantidad_hojas": page_count,
    }


def _extract_fields(pdf_path: str) -> tuple[dict, str]:
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
            }, "credit_card"

        first_page_text = pages[0].full_text
        doc_type = detect_document_type(first_page_text)

        if doc_type == "credit_card":
            campos = _extract_fields_credit_card(pages, page_count)
        else:
            campos = _extract_fields_notarized(pages, page_count)

        return campos, doc_type
    finally:
        doc.close()


def process_pdf(pdf_path: str, nombre_carpeta: str) -> ContratoSchema:
    """Procesa un PDF y retorna un ContratoSchema validado."""
    nombre_archivo = os.path.basename(pdf_path)

    try:
        campos, doc_type = _extract_fields(pdf_path)
    except Exception as e:
        logger.error("Error procesando %s: %s", pdf_path, e)
        return ContratoSchema(
            nombre_archivo=nombre_archivo,
            nombre_carpeta=nombre_carpeta,
            estado_extraccion=EstadoExtraccion.ERROR,
            observaciones=str(e),
        )

    estado, observaciones = validate_campos(campos)

    return ContratoSchema(
        nombre_completo=campos["nombre_completo"],
        rut=campos["rut"],
        fecha_contrato=campos["fecha_contrato"],
        proto=(
            int(campos["proto"])
            if campos["proto"] and campos["proto"].isdigit()
            else None
        ),
        repertorio=(
            int(campos["repertorio"])
            if campos["repertorio"] and campos["repertorio"].isdigit()
            else None
        ),
        fecha_repertorio=campos["fecha_repertorio"],
        nombre_archivo=nombre_archivo,
        cantidad_hojas=campos["cantidad_hojas"],
        nombre_carpeta=nombre_carpeta,
        estado_extraccion=estado,
        observaciones=observaciones,
    )
