"""Widget zona de drag & drop para carpetas."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class DropZone(QFrame):
    """Área de arrastrar y soltar carpetas.

    Emite folder_selected(str) cuando se suelta una carpeta válida.
    """

    folder_selected = Signal(str)
    folder_cleared = Signal()

    def __init__(
        self,
        parent=None,
        on_drop_callback: Optional[Callable[[str], None]] = None,
        on_clear_callback: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._selected_path: Optional[str] = None
        self._on_drop_callback = on_drop_callback
        self._on_clear_callback = on_clear_callback

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(
            "Arrastra una carpeta con PDFs aquí\n"
            "o haz clic para seleccionar",
            self,
        )
        self._label.setObjectName("dropAreaText")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - override de Qt
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                path = urls[0].toLocalFile()
                if Path(path).is_dir():
                    event.acceptProposedAction()
                    self.setProperty("dragActive", True)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - override de Qt
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 - override de Qt
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                path = urls[0].toLocalFile()
                if Path(path).is_dir():
                    self._set_selected_path(path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - override de Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_folder_dialog()

    def _open_folder_dialog(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                self._set_selected_path(selected[0])

    def _set_selected_path(self, path: str) -> None:
        self._selected_path = path
        self._label.setText(f"📁 {path}")
        self.folder_selected.emit(path)
        if self._on_drop_callback:
            self._on_drop_callback(path)

    def get_selected_path(self) -> Optional[str]:
        return self._selected_path

    def clear(self) -> None:
        self._selected_path = None
        self._label.setText(
            "Arrastra una carpeta con PDFs aquí\n"
            "o haz clic para seleccionar"
        )
        self.folder_cleared.emit()
        if self._on_clear_callback:
            self._on_clear_callback()

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - override de Qt
        super().setEnabled(enabled)
        self.setAcceptDrops(enabled)
