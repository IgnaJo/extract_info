"""Worker para procesamiento en hilo secundario (QThread)."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal

from extract_info.pipelines.base import NodeResult
from extract_info.pipelines.retail import retail_process_folder
from extract_info.pipelines.aseguradora import aseguradora_process_folder


class PDFWorker(QObject):
    """Worker que ejecuta el procesamiento de PDFs en un hilo separado.

    Emite señales para progreso, completado y error.
    """

    progress = Signal(int, int, str)      # current, total, filename
    completed = Signal(object)            # NodeResult
    failed = Signal(str)                  # error message

    def __init__(
        self,
        node_name: str,
        folder_path: str,
        pause_event: Optional[threading.Event] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._node_name = node_name
        self._folder_path = folder_path
        self._pause_event = pause_event
        self._cancel_check = cancel_check
        self._thread: Optional[QThread] = None

    def start(self) -> None:
        """Inicia el worker en un QThread nuevo."""
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self.run)
        self._thread.start()

    def run(self) -> None:
        """Ejecuta el procesamiento de la carpeta."""
        try:
            def progress_cb(current: int, total: int, filename: str) -> None:
                self.progress.emit(current, total, filename)

            def cancel_cb() -> bool:
                return self._cancel_check() if self._cancel_check else False

            if self._node_name == "Retail":
                result = retail_process_folder(
                    self._folder_path,
                    progress_callback=progress_cb,
                    cancel_check=cancel_cb,
                    pause_event=self._pause_event,
                )
            elif self._node_name == "Aseguradora":
                result = aseguradora_process_folder(
                    self._folder_path,
                    progress_callback=progress_cb,
                    cancel_check=cancel_cb,
                    pause_event=self._pause_event,
                )
            else:
                raise ValueError(f"Nodo desconocido: {self._node_name}")

            self.completed.emit(result)

        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if self._thread:
                self._thread.quit()
                self._thread.wait()

    def stop(self) -> None:
        """Detiene el worker y su hilo."""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()