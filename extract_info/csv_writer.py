"""Escritura de archivos CSV por carpeta contenedora."""

from __future__ import annotations

import logging
import os

import pandas as pd

from extract_info.batch import FolderResult

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "nombre_archivo",
    "nombre_completo",
    "rut",
    "fecha_contrato",
    "proto",
    "repertorio",
    "fecha_repertorio",
    "cantidad_hojas",
    "nombre_carpeta",
    "estado_extraccion",
    "observaciones",
]


def result_to_row(doc) -> dict:
    """Convierte un ContratoSchema a diccionario para CSV."""
    return {
        "nombre_archivo": doc.nombre_archivo,
        "nombre_completo": doc.nombre_completo,
        "rut": doc.rut,
        "fecha_contrato": doc.fecha_contrato,
        "proto": doc.proto,
        "repertorio": doc.repertorio,
        "fecha_repertorio": doc.fecha_repertorio,
        "cantidad_hojas": doc.cantidad_hojas,
        "nombre_carpeta": doc.nombre_carpeta,
        "estado_extraccion": doc.estado_extraccion.value,
        "observaciones": doc.observaciones,
    }


def write_folder_csv(folder_result: FolderResult, output_dir: str) -> str:
    """Escribe un CSV para una carpeta procesada.

    Args:
        folder_result: Resultado del procesamiento de la carpeta.
        output_dir: Directorio donde se guardará el CSV.

    Returns:
        Ruta del archivo CSV generado.
    """
    os.makedirs(output_dir, exist_ok=True)

    filename = f"resultado_{folder_result.nombre_carpeta}.csv"
    filepath = os.path.join(output_dir, filename)

    rows = [result_to_row(doc) for doc in folder_result.documentos]
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)

    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info("CSV generado: %s (%d registros)", filepath, len(rows))

    return filepath


def write_all_csvs(
    folder_results: list[FolderResult], output_dir: str
) -> list[str]:
    """Escribe CSVs para todas las carpetas procesadas.

    Returns:
        Lista de rutas de archivos CSV generados.
    """
    paths = []
    for result in folder_results:
        if result.documentos:
            path = write_folder_csv(result, output_dir)
            paths.append(path)
        else:
            logger.warning("Carpeta %s sin documentos, omitiendo CSV", result.nombre_carpeta)
    return paths


def write_unified_csv(
    folder_results: list[FolderResult], output_dir: str, filename: str = "resultado_unificado.csv"
) -> str:
    """Escribe un único CSV unificado con todos los documentos de todas las carpetas.

    Args:
        folder_results: Lista de resultados de todas las carpetas procesadas.
        output_dir: Directorio donde se guardará el CSV.
        filename: Nombre del archivo CSV (por defecto: resultado_unificado.csv).

    Returns:
        Ruta del archivo CSV generado.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    all_rows = []
    for result in folder_results:
        for doc in result.documentos:
            all_rows.append(result_to_row(doc))

    df = pd.DataFrame(all_rows, columns=CSV_COLUMNS)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info("CSV unificado generado: %s (%d registros)", filepath, len(all_rows))

    return filepath
