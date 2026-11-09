"""Tipos base para pipelines de extracción."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional


@dataclass
class LogEntry:
    """Entrada de log estructurada."""
    timestamp: str
    level: str
    message: str
    filename: Optional[str] = None
    node_name: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class NodeResult:
    """Resultado del procesamiento de un nodo."""
    rows: List[dict]
    columns: List[str]
    logs: List[LogEntry]
    total_processed: int = 0
    success_count: int = 0
    warning_count: int = 0
    error_count: int = 0


# Node metadata - simple dict instead of registry
NODE_SPECS = {
    "Retail": {
        "name": "Retail",
        "description": "Contratos de tarjeta de crédito - Retail",
        "csv_columns": [
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
        ],
    },
    "Aseguradora": {
        "name": "Aseguradora",
        "description": "Documentos de Aseguradora - Notarial",
        "csv_columns": [
            "Archivo",
            "Fecha Firma",
            "RUN Firmante",
            "Nombre Firmante",
            "REP Nº",
            "PROTOCOLIZADO Nº",
            "REP Fecha",
            "Cantidad de páginas",
            "Estado",
        ],
    },
}


def list_nodes() -> List[str]:
    """Retorna lista de nombres de nodos disponibles."""
    return sorted(NODE_SPECS.keys())


def get_node_spec(name: str) -> dict | None:
    """Obtiene la especificación de un nodo por nombre."""
    return NODE_SPECS.get(name)


def process_folder(
    folder_path: str,
    process_single: Callable[[str], dict],
    node_name: str,
    csv_columns: List[str],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    pause_event: Optional[Any] = None,
) -> NodeResult:
    """Procesa una carpeta completa usando la función process_single provista.

    Args:
        folder_path: Ruta a la carpeta con PDFs.
        process_single: Función que procesa un solo PDF y retorna dict.
        node_name: Nombre del nodo (para logs).
        csv_columns: Lista de columnas del CSV de salida.
        progress_callback: Función opcional para reportar progreso.
        cancel_check: Función opcional que retorna True si se debe cancelar.
        pause_event: Objeto threading.Event opcional.

    Returns:
        NodeResult con todas las filas procesadas y logs.
    """
    import logging
    from datetime import datetime

    from extract_info.extraction.file_discovery import discover_pdf_files

    logger = logging.getLogger(__name__)
    logs: List[LogEntry] = []
    rows: List[dict] = []

    pdf_files = discover_pdf_files(folder_path)

    total = len(pdf_files)
    success_count = 0
    warning_count = 0
    error_count = 0
    cancelled = False

    for i, discovered_file in enumerate(pdf_files, 1):
        filename = discovered_file.relative_path
        if pause_event is not None:
            pause_event.wait()

        if cancel_check and cancel_check():
            for remaining in pdf_files[i - 1:]:
                log_entry = LogEntry(
                    timestamp=datetime.now().isoformat(),
                    level="WARNING",
                    message=f"{remaining.relative_path} → CANCELADO",
                    filename=remaining.relative_path,
                    node_name=node_name,
                )
                logs.append(log_entry)
            cancelled = True
            break

        pdf_path = discovered_file.path

        if progress_callback:
            progress_callback(i, total, filename)

        try:
            row = process_single(pdf_path)
            for column in ("nombre_archivo", "Archivo"):
                if column in row:
                    row[column] = filename
                    break
            rows.append(row)

            estado = row.get("Estado", row.get("estado_extraccion", ""))
            if "OK" in str(estado).upper() or "EXITO" in str(estado).upper():
                success_count += 1
                level = "INFO"
            elif "REVISAR" in str(estado).upper() or "ADVERTENCIA" in str(estado).upper():
                warning_count += 1
                level = "WARNING"
            else:
                error_count += 1
                level = "ERROR"

            log_entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                level=level,
                message=f"{filename} → {estado}",
                filename=filename,
                node_name=node_name,
            )
            logs.append(log_entry)
            logger.log(
                getattr(logging, level),
                "[%s] %s → %s",
                node_name,
                filename,
                estado,
            )

        except Exception as e:
            error_count += 1
            error_row = _create_error_row(filename, str(e), csv_columns)
            rows.append(error_row)

            log_entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                level="ERROR",
                message=f"{filename} → ERROR: {e}",
                filename=filename,
                node_name=node_name,
                details={"error": str(e)},
            )
            logs.append(log_entry)
            logger.error("[%s] %s → ERROR: %s", node_name, filename, e)

    return NodeResult(
        rows=rows,
        columns=csv_columns,
        logs=logs,
        total_processed=total,
        success_count=success_count,
        warning_count=warning_count,
        error_count=error_count,
    )


def _create_error_row(filename: str, error_msg: str, csv_columns: List[str]) -> dict:
    """Crea una fila de error con valores por defecto."""
    row = {}
    for col in csv_columns:
        col_lower = col.lower()
        if "archivo" in col_lower:
            row[col] = filename
        elif "estado" in col_lower:
            row[col] = f"ERROR: {error_msg}"
        elif "pagina" in col_lower:
            row[col] = 0
        else:
            row[col] = None
    return row