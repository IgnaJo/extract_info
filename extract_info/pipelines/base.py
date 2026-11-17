"""Tipos base para pipelines de extracción."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence

from extract_info.columns import (
    ColumnKind,
    ColumnSpec,
    column_keys,
    find_kind,
)


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
        "columns": (
            ColumnSpec("nombre_archivo", "Archivo", ColumnKind.FILENAME),
            ColumnSpec("rut", "RUT"),
            ColumnSpec("nombre_completo", "Nombre Completo"),
            ColumnSpec("fecha_contrato", "Fecha Contrato", ColumnKind.DATE),
            ColumnSpec("proto", "Nº Proto"),
            ColumnSpec("repertorio", "Repertorio"),
            ColumnSpec("fecha_repertorio", "Fecha Repertorio", ColumnKind.DATE),
            ColumnSpec("cantidad_hojas", "Hojas", ColumnKind.NUMBER),
            ColumnSpec("nombre_carpeta", "Carpeta", ColumnKind.FOLDER),
            ColumnSpec("estado_extraccion", "Estado", ColumnKind.STATUS),
            ColumnSpec("observaciones", "Observaciones", ColumnKind.NOTES),
        ),
    },
    "Aseguradora": {
        "name": "Aseguradora",
        "description": "Documentos de Aseguradora - Notarial",
        "columns": (
            ColumnSpec("Archivo", "Archivo", ColumnKind.FILENAME),
            ColumnSpec("Fecha Firma", "Fecha Firma", ColumnKind.DATE),
            ColumnSpec("RUN Firmante", "RUN Firmante"),
            ColumnSpec("Nombre Firmante", "Nombre"),
            ColumnSpec("REP Nº", "REP Nº"),
            ColumnSpec("PROTOCOLIZADO Nº", "Nº Proto"),
            ColumnSpec("REP Fecha", "REP Fecha", ColumnKind.DATE),
            ColumnSpec("Cantidad de páginas", "Hojas", ColumnKind.NUMBER),
            ColumnSpec("Estado", "Estado", ColumnKind.STATUS),
        ),
    },
    "Banco": {
        "name": "Banco",
        "description": "Contratos de crédito de consumo - Banco",
        "columns": (
            ColumnSpec("numero operacion", "numero operacion"),
            ColumnSpec("fecha firma", "fecha firma", ColumnKind.DATE),
            ColumnSpec("rut", "rut"),
            ColumnSpec("nombre", "nombre"),
            ColumnSpec("nº repertorio", "nº repertorio"),
            ColumnSpec("Nº proto", "Nº proto"),
            ColumnSpec("fecha repertorio", "fecha repertorio", ColumnKind.DATE),
            ColumnSpec(
                "número de paginas documento",
                "número de paginas documento",
                ColumnKind.NUMBER,
            ),
            ColumnSpec("Archivo", "Archivo", ColumnKind.FILENAME),
            ColumnSpec("Estado", "Estado", ColumnKind.STATUS),
        ),
    },
}

# ``csv_columns`` se deriva del esquema para no duplicar la verdad.
for _spec in NODE_SPECS.values():
    _spec["csv_columns"] = column_keys(_spec["columns"])


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
    columns: Sequence[ColumnSpec],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    pause_event: Optional[Any] = None,
) -> NodeResult:
    """Procesa una carpeta completa usando la función process_single provista.

    Args:
        folder_path: Ruta a la carpeta con PDFs.
        process_single: Función que procesa un solo PDF y retorna dict.
        node_name: Nombre del nodo (para logs).
        columns: Esquema declarativo de columnas del CSV de salida.
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
    csv_columns = column_keys(columns)
    filename_column = find_kind(columns, ColumnKind.FILENAME)
    status_column = find_kind(columns, ColumnKind.STATUS)
    status_key = status_column.key if status_column else None
    logs: List[LogEntry] = []
    rows: List[dict] = []

    pdf_files = discover_pdf_files(folder_path)

    total = len(pdf_files)
    success_count = 0
    warning_count = 0
    error_count = 0

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
            break

        pdf_path = discovered_file.path

        if progress_callback:
            progress_callback(i, total, filename)

        try:
            row = process_single(pdf_path)
            unknown = set(row) - set(csv_columns)
            if unknown:
                raise ValueError(f"columnas no declaradas: {sorted(unknown)}")
            if filename_column is not None and filename_column.key in row:
                row[filename_column.key] = filename
            rows.append(row)

            estado = row.get(status_key, "") if status_key else ""
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
            error_row = _create_error_row(filename, str(e), columns)
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


def _create_error_row(
    filename: str, error_msg: str, columns: Sequence[ColumnSpec]
) -> dict:
    """Crea una fila de error usando la semántica declarada de cada columna."""
    row = {}
    for column in columns:
        if column.kind == ColumnKind.FILENAME:
            row[column.key] = filename
        elif column.kind == ColumnKind.STATUS:
            row[column.key] = f"ERROR: {error_msg}"
        elif column.kind == ColumnKind.NUMBER:
            row[column.key] = 0
        else:
            row[column.key] = None
    return row
