"""Nodo Banco: contrato de crédito de consumo (Banco Ripley)."""

from __future__ import annotations

import os
import re

from extract_info.extraction.anchors import find_values_block_near_label
from extract_info.extraction.text_reader import PageData, TextBlock, extract_page_text, open_pdf
from extract_info.pipelines.base import NODE_SPECS, process_folder

PAT_FECHA = re.compile(r"(\d{2}[-/]\d{2}[-/]\d{4})")
PAT_OPERACION = re.compile(r"(\d{6,})")
PAT_RUT = re.compile(r"(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])")
PAT_NOMBRE = re.compile(r"(.+)")

LABEL_FECHA = re.compile(r"^\s*Fecha\s*:?\s*$", re.IGNORECASE)
LABEL_OPERACION = re.compile(r"^\s*N[°º]\s*de\s+Operaci[oó]n\s*:?\s*$", re.IGNORECASE)
LABEL_NOMBRE = re.compile(r"^\s*Nombre\s+Cliente\s*:?\s*$", re.IGNORECASE)
LABEL_RUT = re.compile(r"^\s*C[eé]dula\s+de\s+Identidad\s*:?\s*$", re.IGNORECASE)

# Bloques de formulario vacío: ":", "____", etc.
_FORM_SCAFFOLD = re.compile(r"^[:.\s_]+$")

# Fila de valores de hoja 1 en la esquina superior derecha.
PAT_REPERTORIO_ROW = re.compile(r"(\d{4,7})\s+(\d{4,7})\s+(\d{2}[-/]\d{2}[-/]\d{4})")


def _first_group(match: re.Match) -> str:
    value = match.group(1) if match.groups() else match.group(0)
    return value.strip()


def _normalize_date(value: str | None) -> str | None:
    return value.replace("/", "-") if value else None


def _find_row_value(
    blocks: list[TextBlock], label_pattern: re.Pattern, value_pattern: re.Pattern
) -> str | None:
    """Busca el valor de una fila etiqueta/valor de la hoja de suscripción.

    El valor puede estar en el mismo bloque tras la etiqueta o en el bloque
    vecino de la derecha (misma banda vertical), ignorando el andamiaje del
    formulario (": ____") y validando con ``value_pattern``.
    """
    for label_block in blocks:
        match = label_pattern.search(label_block.text)
        if not match:
            continue

        tail = label_block.text[match.end() :].strip()
        found = value_pattern.search(tail)
        if found:
            return _first_group(found)

        label_center = (label_block.top + label_block.bottom) / 2
        candidates = []
        for block in blocks:
            if block is label_block or block.left <= label_block.left:
                continue
            if abs((block.top + block.bottom) / 2 - label_center) > 10:
                continue
            text = block.text.strip()
            if not text or _FORM_SCAFFOLD.match(text):
                continue
            candidates.append((block.left, block))

        candidates.sort(key=lambda item: item[0])
        for _left, block in candidates:
            found = value_pattern.search(block.text)
            if found:
                return _first_group(found)

    return None


def _extract_repertorio(page: PageData) -> tuple[str | None, str | None, str | None]:
    """Extrae (proto, repertorio, fecha_repertorio) de la esquina superior derecha."""
    proto = repertorio = fecha = None

    values = find_values_block_near_label(
        page.blocks, re.compile(r"PROTOCOLIZADO", re.IGNORECASE), num_values=3
    )
    if values and len(values) >= 2:
        proto, repertorio = values[0], values[1]
        if len(values) >= 3:
            fecha_match = PAT_FECHA.search(values[2])
            fecha = fecha_match.group(1) if fecha_match else None

    if not (proto and repertorio):
        for block in page.blocks:
            if block.left < 350 or block.top > 120:
                continue
            match = PAT_REPERTORIO_ROW.search(block.text)
            if match:
                proto, repertorio, fecha = match.groups()
                break

    return proto, repertorio, _normalize_date(fecha)


def _extract_suscription(page: PageData) -> dict:
    """Extrae los campos de la hoja 9 (página de suscripción del contrato)."""
    nombre = _find_row_value(page.blocks, LABEL_NOMBRE, PAT_NOMBRE)
    if nombre:
        nombre = nombre.split("\n")[0].strip()

    return {
        "numero operacion": _find_row_value(page.blocks, LABEL_OPERACION, PAT_OPERACION),
        "fecha firma": _normalize_date(_find_row_value(page.blocks, LABEL_FECHA, PAT_FECHA)),
        "rut": _find_row_value(page.blocks, LABEL_RUT, PAT_RUT),
        "nombre": nombre,
    }


def _verificar_estado(
    operacion: str | None,
    fecha: str | None,
    rut: str | None,
    nombre: str | None,
    repertorio: str | None,
    proto: str | None,
    fecha_repertorio: str | None,
    paginas: int,
) -> str:
    errores = []
    if not operacion:
        errores.append("Nº operación")
    if not fecha:
        errores.append("Fecha firma")
    if not rut:
        errores.append("RUT")
    if not nombre:
        errores.append("Nombre")
    if not repertorio:
        errores.append("Nº repertorio")
    if not proto:
        errores.append("Nº proto")
    if not fecha_repertorio:
        errores.append("Fecha repertorio")
    if not paginas or paginas < 1:
        errores.append("Páginas")

    return "OK" if not errores else "REVISAR: " + ", ".join(errores)


def _build_row(
    *,
    operacion: str | None,
    fecha: str | None,
    rut: str | None,
    nombre: str | None,
    repertorio: str | None,
    proto: str | None,
    fecha_repertorio: str | None,
    paginas: int,
    archivo: str,
    estado: str,
) -> dict:
    return {
        "numero operacion": operacion,
        "fecha firma": fecha,
        "rut": rut,
        "nombre": nombre,
        "nº repertorio": repertorio,
        "Nº proto": proto,
        "fecha repertorio": fecha_repertorio,
        "número de paginas documento": paginas,
        "Archivo": archivo,
        "Estado": estado,
    }


def banco_process_single(pdf_path: str) -> dict:
    """Procesa un PDF de Banco y retorna una fila del CSV de salida."""
    archivo = os.path.splitext(os.path.basename(pdf_path))[0]

    doc = open_pdf(pdf_path)
    try:
        page_count = len(doc)
        if page_count < 9:
            return _build_row(
                operacion=None,
                fecha=None,
                rut=None,
                nombre=None,
                repertorio=None,
                proto=None,
                fecha_repertorio=None,
                paginas=page_count,
                archivo=archivo,
                estado=f"ERROR: documento sin hoja 9 ({page_count} páginas)",
            )

        first_page = extract_page_text(doc[0])
        suscription = extract_page_text(doc[8])
    finally:
        doc.close()

    proto, repertorio, fecha_repertorio = _extract_repertorio(first_page)
    campos = _extract_suscription(suscription)
    estado = _verificar_estado(
        campos["numero operacion"],
        campos["fecha firma"],
        campos["rut"],
        campos["nombre"],
        repertorio,
        proto,
        fecha_repertorio,
        page_count,
    )

    return _build_row(
        operacion=campos["numero operacion"],
        fecha=campos["fecha firma"],
        rut=campos["rut"],
        nombre=campos["nombre"],
        repertorio=repertorio,
        proto=proto,
        fecha_repertorio=fecha_repertorio,
        paginas=page_count,
        archivo=archivo,
        estado=estado,
    )


def banco_process_folder(
    folder_path: str,
    progress_callback=None,
    cancel_check=None,
    pause_event=None,
):
    """Procesa una carpeta con el pipeline Banco."""
    spec = NODE_SPECS["Banco"]
    return process_folder(
        folder_path=folder_path,
        process_single=banco_process_single,
        node_name=spec["name"],
        columns=spec["columns"],
        progress_callback=progress_callback,
        cancel_check=cancel_check,
        pause_event=pause_event,
    )
