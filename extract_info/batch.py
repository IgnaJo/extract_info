"""Procesamiento por lotes con escaneo recursivo de directorios."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from extract_info.extraction.file_discovery import discover_pdf_files
from extract_info.models import ContratoSchema
from extract_info.pipeline import process_pdf
from extract_info.pipelines.aseguradora import aseguradora_process_folder
from extract_info.pipelines.retail import retail_process_folder

logger = logging.getLogger(__name__)

MAX_PDFS_PER_FOLDER = 100

_PIPELINE_RUNNERS = {
    "retail": retail_process_folder,
    "aseguradora": aseguradora_process_folder,
}


def list_pipelines() -> list[str]:
    """Nombres de pipelines disponibles para el CLI."""
    return sorted(_PIPELINE_RUNNERS)


@dataclass
class FolderResult:
    """Resultado del procesamiento de una carpeta."""

    nombre_carpeta: str
    ruta_carpeta: str
    documentos: list[ContratoSchema]


def scan_folders(root_path: str) -> list[str]:
    """Escanea recursivamente el directorio raíz buscando carpetas con PDFs.

    Retorna una lista de rutas de carpetas que contienen al menos 1 PDF.
    """
    folders_with_pdfs = {
        os.path.dirname(discovered_file.path)
        for discovered_file in discover_pdf_files(root_path)
    }
    return sorted(folders_with_pdfs)


def process_folder(folder_path: str) -> FolderResult:
    """Procesa todos los PDFs de una carpeta.

    Retorna FolderResult con los documentos procesados.
    """
    nombre_carpeta = os.path.basename(os.path.normpath(folder_path))
    pdf_files = sorted(
        f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")
    )

    # Limitar a MAX_PDFS_PER_FOLDER
    if len(pdf_files) > MAX_PDFS_PER_FOLDER:
        logger.warning(
            "Carpeta %s tiene %d PDFs, procesando solo los primeros %d",
            nombre_carpeta,
            len(pdf_files),
            MAX_PDFS_PER_FOLDER,
        )
        pdf_files = pdf_files[:MAX_PDFS_PER_FOLDER]

    documentos = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        try:
            doc = process_pdf(pdf_path, nombre_carpeta)
            documentos.append(doc)
        except Exception as e:
            logger.error("Error procesando %s: %s", pdf_path, e)

    return FolderResult(
        nombre_carpeta=nombre_carpeta,
        ruta_carpeta=folder_path,
        documentos=documentos,
    )


def process_batch(
    root_path: str,
    max_workers: int | None = None,
) -> list[FolderResult]:
    """Procesa todas las carpetas con PDFs usando concurrencia.

    Args:
        root_path: Directorio raíz para escanear.
        max_workers: Número máximo de procesos paralelos (None = default).

    Returns:
        Lista de FolderResult, uno por cada carpeta procesada.
    """
    folders = scan_folders(root_path)
    if not folders:
        logger.warning("No se encontraron carpetas con PDFs en %s", root_path)
        return []

    logger.info("Encontradas %d carpetas con PDFs", len(folders))

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_folder = {
            executor.submit(process_folder, folder): folder for folder in folders
        }

        for future in as_completed(future_to_folder):
            folder = future_to_folder[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(
                    "Carpeta %s: %d documentos procesados",
                    result.nombre_carpeta,
                    len(result.documentos),
                )
            except Exception as e:
                logger.error("Error procesando carpeta %s: %s", folder, e)

    results.sort(key=lambda r: r.nombre_carpeta)
    return results


@dataclass
class PipelineFolderResult:
    """Filas y columnas de una carpeta procesada por un pipeline seleccionable."""

    nombre_carpeta: str
    rows: list[dict]
    columns: list[str]


def process_folder_pipeline(folder_path: str, pipeline: str = "retail") -> PipelineFolderResult:
    """Procesa una carpeta con el pipeline indicado."""
    try:
        runner = _PIPELINE_RUNNERS[pipeline]
    except KeyError:
        raise ValueError(
            f"Pipeline desconocido: {pipeline!r}. Opciones: {', '.join(list_pipelines())}"
        ) from None

    node_result = runner(folder_path)
    return PipelineFolderResult(
        nombre_carpeta=os.path.basename(os.path.normpath(folder_path)),
        rows=node_result.rows,
        columns=node_result.columns,
    )


def process_batch_pipeline(
    root_path: str,
    pipeline: str = "retail",
    max_workers: int | None = None,
) -> list[PipelineFolderResult]:
    """Procesa todas las carpetas con PDFs usando el pipeline indicado."""
    if pipeline not in _PIPELINE_RUNNERS:
        raise ValueError(
            f"Pipeline desconocido: {pipeline!r}. Opciones: {', '.join(list_pipelines())}"
        )

    folders = scan_folders(root_path)
    if not folders:
        logger.warning("No se encontraron carpetas con PDFs en %s", root_path)
        return []

    logger.info("Encontradas %d carpetas con PDFs", len(folders))

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_folder = {
            executor.submit(process_folder_pipeline, folder, pipeline): folder
            for folder in folders
        }

        for future in as_completed(future_to_folder):
            folder = future_to_folder[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(
                    "Carpeta %s: %d documentos procesados",
                    result.nombre_carpeta,
                    len(result.rows),
                )
            except Exception as e:
                logger.error("Error procesando carpeta %s: %s", folder, e)

    results.sort(key=lambda r: r.nombre_carpeta)
    return results
