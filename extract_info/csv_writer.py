"""Escritura de archivos CSV por carpeta contenedora (stdlib only)."""

from __future__ import annotations

import csv
import logging
import os

from extract_info.batch import FolderResult, PipelineFolderResult

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


def _write_rows(filepath: str, rows: list[dict], columns: list[str]) -> None:
    """Escribe filas con las columnas indicadas (UTF-8 BOM)."""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


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
    _write_rows(filepath, rows, CSV_COLUMNS)

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

def write_pipeline_csvs(
    results: list[PipelineFolderResult],
    output_dir: str,
    unified: bool = False,
) -> list[str]:
    """Escribe CSVs para resultados de cualquier pipeline.

    Con ``unified=True`` genera un único ``resultado_unificado.csv``;
    si no, un CSV por carpeta con el mismo nombre que el flujo Retail.
    """
    os.makedirs(output_dir, exist_ok=True)
    if not results:
        return []

    columns = results[0].columns

    if unified:
        filepath = os.path.join(output_dir, "resultado_unificado.csv")
        rows = [row for result in results for row in result.rows]
        _write_rows(filepath, rows, columns)
        logger.info("CSV unificado generado: %s (%d registros)", filepath, len(rows))
        return [filepath]

    paths = []
    for result in results:
        if not result.rows:
            logger.warning(
                "Carpeta %s sin documentos, omitiendo CSV", result.nombre_carpeta
            )
            continue
        filepath = os.path.join(output_dir, f"resultado_{result.nombre_carpeta}.csv")
        _write_rows(filepath, result.rows, result.columns)
        logger.info("CSV generado: %s (%d registros)", filepath, len(result.rows))
        paths.append(filepath)
    return paths
