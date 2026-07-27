"""Procesamiento por lotes con escaneo recursivo de directorios."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from extract_info.models import ContratoSchema
from extract_info.pipeline import process_pdf

logger = logging.getLogger(__name__)

MAX_PDFS_PER_FOLDER = 100


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
    folders_with_pdfs = []

    for dirpath, _dirnames, filenames in os.walk(root_path):
        pdf_files = [f for f in filenames if f.lower().endswith(".pdf")]
        if pdf_files:
            folders_with_pdfs.append(dirpath)

    return folders_with_pdfs


def get_folder_name(folder_path: str) -> str:
    """Retorna el nombre de la carpeta (último componente de la ruta)."""
    return os.path.basename(folder_path.rstrip("/"))


def process_folder(folder_path: str) -> FolderResult:
    """Procesa todos los PDFs de una carpeta.

    Retorna FolderResult con los documentos procesados.
    """
    nombre_carpeta = get_folder_name(folder_path)
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
