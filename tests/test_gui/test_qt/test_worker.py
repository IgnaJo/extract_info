"""Tests pytest-qt para PDFWorker (simplificados sin threads)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from extract_info.gui.worker import PDFWorker
from extract_info.pipelines.base import NodeResult


@pytest.fixture(scope="session")
def qapp():
    """Fixture para QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_worker_signals_exist(qapp):
    """Worker tiene las señales esperadas."""
    worker = PDFWorker("Retail", "/fake/path")

    # Verificar que las señales existen
    assert hasattr(worker, "progress")
    assert hasattr(worker, "completed")
    assert hasattr(worker, "failed")

    # Verificar tipos de señales
    assert isinstance(worker.progress, Signal)
    assert isinstance(worker.completed, Signal)
    assert isinstance(worker.failed, Signal)


def test_worker_initialization(qapp):
    """Worker se inicializa correctamente."""
    pause_event = MagicMock()
    cancel_check = MagicMock(return_value=False)

    worker = PDFWorker("Retail", "/test/path", pause_event, cancel_check)

    assert worker._node_name == "Retail"
    assert worker._folder_path == "/test/path"
    assert worker._pause_event is pause_event
    assert worker._cancel_check is cancel_check


def test_worker_emits_completed_on_success(qapp):
    """Worker emite completed al terminar correctamente (sin thread)."""
    result_received = {}

    def on_completed(result):
        result_received["result"] = result

    worker = PDFWorker("Retail", "/fake/path")
    worker.completed.connect(on_completed)

    from extract_info.pipelines.base import NodeResult
    mock_result = NodeResult(
        rows=[{"col": "val"}],
        columns=["col"],
        logs=[],
        total_processed=1,
        success_count=1,
    )

    # Ejecutar run() directamente en el hilo principal (sin thread)
    with patch("extract_info.gui.worker.retail_process_folder", return_value=mock_result):
        worker.run()

    assert "result" in result_received
    assert result_received["result"] is mock_result


def test_worker_emits_failed_on_error(qapp):
    """Worker emite failed si hay excepción (sin thread)."""
    error_received = {}

    def on_failed(error):
        error_received["error"] = error

    worker = PDFWorker("Retail", "/fake/path")
    worker.failed.connect(on_failed)

    with patch("extract_info.gui.worker.retail_process_folder", side_effect=RuntimeError("Test error")):
        worker.run()

    assert "error" in error_received
    assert "Test error" in error_received["error"]