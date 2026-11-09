"""Smoke tests de las acciones principales de MainWindow (Run y Export).

Cubren regresiones que no detectaban los tests de widgets:
- NameError por falta de import de QThread al iniciar el procesamiento.
- AttributeError por usar self._current_node (nunca asignado) al exportar.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication

from extract_info.gui import app as app_module
from extract_info.gui.app import MainWindow
from extract_info.pipelines.base import NodeResult


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeWorker(QObject):
    """Worker inerte para probar el armado del QThread sin procesar PDFs."""

    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__()

    def run(self) -> None:
        pass


def test_start_processing_creates_worker_thread(qapp, monkeypatch, tmp_path):
    window = MainWindow()
    window._current_node_name = "Retail"

    monkeypatch.setattr(window.drop_zone, "get_selected_path", lambda: str(tmp_path))
    monkeypatch.setattr(app_module, "PDFWorker", _FakeWorker)

    window._start_processing()

    assert isinstance(window._worker_thread, QThread)
    assert window._worker_thread.isRunning()

    window._worker_thread.quit()
    assert window._worker_thread.wait(3000)
    window.close()


def test_export_csv_uses_current_node_name(qapp, monkeypatch, tmp_path):
    window = MainWindow()
    window._current_node_name = "Retail"
    window._current_result = NodeResult(
        rows=[{"nombre_archivo": "a.pdf", "nombre_completo": "X"}],
        columns=["nombre_archivo", "nombre_completo"],
        logs=[],
        total_processed=1,
        success_count=1,
    )

    out = tmp_path / "out.csv"
    calls = {}

    class _FakeFileDialog:
        @staticmethod
        def getSaveFileName(*args, **kwargs):  # noqa: N802 - nombre de la API de Qt
            calls["default_name"] = args[2]
            return str(out), ""

    class _FakeMessageBox:
        @staticmethod
        def information(*args, **kwargs):
            pass

        @staticmethod
        def critical(*args, **kwargs):
            raise AssertionError(f"no se esperaba error: {args}")

    monkeypatch.setattr(app_module, "QFileDialog", _FakeFileDialog)
    monkeypatch.setattr(app_module, "QMessageBox", _FakeMessageBox)

    window._export_csv()

    assert "Retail" in calls["default_name"]
    assert out.exists()
    content = out.read_text(encoding="utf-8-sig")
    assert "nombre_archivo" in content
    assert "a.pdf" in content
    window.close()
