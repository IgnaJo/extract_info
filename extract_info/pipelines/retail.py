"""Nodo Retail: wrapper del pipeline actual de contratos de tarjeta de crédito."""

from __future__ import annotations

import os

from extract_info.models import ContratoSchema
from extract_info.pipeline import process_pdf
from extract_info.pipelines.base import NODE_SPECS, process_folder


def retail_process_single(pdf_path: str) -> dict:
    """Procesa un solo PDF usando el pipeline de Retail.

    Args:
        pdf_path: Ruta completa al archivo PDF.

    Returns:
        Diccionario con los campos extraídos.
    """
    folder_name = os.path.basename(os.path.dirname(pdf_path))
    result: ContratoSchema = process_pdf(pdf_path, folder_name)

    return {
        "nombre_archivo": result.nombre_archivo,
        "nombre_completo": result.nombre_completo,
        "rut": result.rut,
        "fecha_contrato": result.fecha_contrato,
        "proto": result.proto,
        "repertorio": result.repertorio,
        "fecha_repertorio": result.fecha_repertorio,
        "cantidad_hojas": result.cantidad_hojas,
        "nombre_carpeta": result.nombre_carpeta,
        "estado_extraccion": result.estado_extraccion.value,
        "observaciones": result.observaciones,
    }


def retail_process_folder(
    folder_path: str,
    progress_callback=None,
    cancel_check=None,
    pause_event=None,
):
    """Procesa una carpeta con el pipeline Retail."""
    spec = NODE_SPECS["Retail"]
    return process_folder(
        folder_path=folder_path,
        process_single=retail_process_single,
        node_name=spec["name"],
        csv_columns=spec["csv_columns"],
        progress_callback=progress_callback,
        cancel_check=cancel_check,
        pause_event=pause_event,
    )
