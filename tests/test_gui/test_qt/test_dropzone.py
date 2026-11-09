"""Tests pytest-qt para DropZone."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtWidgets import QApplication

from extract_info.gui.widgets.drop_zone import DropZone


@pytest.fixture(scope="session")
def qapp():
    """Fixture para QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_dropzone_accepts_directory(qapp, tmp_path):
    """DropZone acepta directorio válido."""
    drop_zone = DropZone()

    # Crear directorio temporal
    test_dir = tmp_path / "test_folder"
    test_dir.mkdir()

    # Simular drag enter con URL de directorio
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(test_dir))])

    event = MagicMock()
    event.mimeData.return_value = mime
    event.acceptProposedAction = MagicMock()

    drop_zone.dragEnterEvent(event)
    event.acceptProposedAction.assert_called()


def test_dropzone_rejects_file(qapp, tmp_path):
    """DropZone rechaza archivo (no directorio)."""
    drop_zone = DropZone()

    test_file = tmp_path / "test.pdf"
    test_file.write_text("fake")

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(test_file))])

    event = MagicMock()
    event.mimeData.return_value = mime
    event.ignore = MagicMock()

    drop_zone.dragEnterEvent(event)
    event.ignore.assert_called()


def test_dropzone_emits_folder_selected(qapp, tmp_path):
    """DropZone emite folder_selected al soltar directorio."""
    callback = MagicMock()
    drop_zone = DropZone(on_drop_callback=callback)

    test_dir = tmp_path / "test_folder"
    test_dir.mkdir()

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(test_dir))])

    event = MagicMock()
    event.mimeData.return_value = mime
    event.acceptProposedAction = MagicMock()

    drop_zone.dropEvent(event)

    callback.assert_called_once_with(str(test_dir))


def test_dropzone_clear_emits_cleared(qapp):
    """DropZone emite folder_cleared al limpiar."""
    callback = MagicMock()
    drop_zone = DropZone(on_clear_callback=callback)

    drop_zone.clear()

    callback.assert_called_once()
    assert drop_zone.get_selected_path() is None


def test_dropzone_get_selected_path(qapp, tmp_path):
    """get_selected_path retorna la ruta seleccionada."""
    drop_zone = DropZone()

    test_dir = tmp_path / "test_folder"
    test_dir.mkdir()

    drop_zone._set_selected_path(str(test_dir))

    assert drop_zone.get_selected_path() == str(test_dir)


def test_dropzone_drag_active_property(qapp, tmp_path):
    """Property dragActive se actualiza en dragEnter/dragLeave."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent

    drop_zone = DropZone()

    test_dir = tmp_path / "test_folder"
    test_dir.mkdir()

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(test_dir))])

    # Crear eventos reales de Qt (usar QPoint, no QPointF)
    enter_event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    drop_zone.dragEnterEvent(enter_event)
    assert drop_zone.property("dragActive") is True

    leave_event = QDragLeaveEvent()
    drop_zone.dragLeaveEvent(leave_event)
    assert drop_zone.property("dragActive") is False
