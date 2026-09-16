"""Interfaz abstracta para nodos de extracción."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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


class BaseNode(ABC):
    """Interfaz base para nodos de extracción.

    Cada nodo encapsula un pipeline de extracción específico
    y define su propio formato de CSV de salida.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre legible del nodo (ej: 'Retail', 'Aseguradora')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción corta del nodo."""
        ...

    @property
    @abstractmethod
    def csv_columns(self) -> List[str]:
        """Columnas del CSV de salida (único por nodo)."""
        ...

    @abstractmethod
    def process_single(self, pdf_path: str) -> dict:
        """Procesa un solo PDF y retorna un dict con los campos.

        Args:
            pdf_path: Ruta completa al archivo PDF.

        Returns:
            Diccionario con los campos extraídos, incluyendo las columnas
            definidas en csv_columns.
        """
        ...

    def process_folder(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        pause_event: Optional[Any] = None,
    ) -> NodeResult:
        """Procesa una carpeta completa y retorna resultados.

        Args:
            folder_path: Ruta a la carpeta con PDFs.
            progress_callback: Función opcional para reportar progreso.
                Signature: (current: int, total: int, filename: str) -> None
            cancel_check: Función opcional que retorna True si se debe cancelar.
                Se llama antes de procesar cada archivo.
            pause_event: Objeto threading.Event opcional. Si se pasa,
                el loop hace .wait() antes de cada archivo (bloquea si está pausado).

        Returns:
            NodeResult con todas las filas procesadas y logs.
        """
        import os
        import logging
        from datetime import datetime

        logger = logging.getLogger(__name__)
        logs: List[LogEntry] = []
        rows: List[dict] = []

        pdf_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(".pdf")
        ]

        total = len(pdf_files)
        success_count = 0
        warning_count = 0
        error_count = 0
        cancelled = False

        for i, filename in enumerate(pdf_files, 1):
            # Pausa: bloquea el hilo mientras el evento esté en estado "set"
            if pause_event is not None:
                pause_event.wait()

            # Cancelación
            if cancel_check and cancel_check():
                cancelled = True
                for remaining in pdf_files[i - 1:]:
                    log_entry = LogEntry(
                        timestamp=datetime.now().isoformat(),
                        level="WARNING",
                        message=f"{remaining} → CANCELADO",
                        filename=remaining,
                        node_name=self.name,
                    )
                    logs.append(log_entry)
                break

            pdf_path = os.path.join(folder_path, filename)

            if progress_callback:
                progress_callback(i, total, filename)

            try:
                row = self.process_single(pdf_path)
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
                    node_name=self.name,
                )
                logs.append(log_entry)
                logger.log(
                    getattr(logging, level),
                    "[%s] %s → %s",
                    self.name,
                    filename,
                    estado,
                )

            except Exception as e:
                error_count += 1
                error_row = self._create_error_row(filename, str(e))
                rows.append(error_row)

                log_entry = LogEntry(
                    timestamp=datetime.now().isoformat(),
                    level="ERROR",
                    message=f"{filename} → ERROR: {e}",
                    filename=filename,
                    node_name=self.name,
                    details={"error": str(e)},
                )
                logs.append(log_entry)
                logger.error("[%s] %s → ERROR: %s", self.name, filename, e)

        return NodeResult(
            rows=rows,
            columns=self.csv_columns,
            logs=logs,
            total_processed=total,
            success_count=success_count,
            warning_count=warning_count,
            error_count=error_count,
        )

    def _create_error_row(self, filename: str, error_msg: str) -> dict:
        """Crea una fila de error con valores por defecto.

        Override en subclases para personalizar el formato de error.
        """
        row = {}
        for col in self.csv_columns:
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
