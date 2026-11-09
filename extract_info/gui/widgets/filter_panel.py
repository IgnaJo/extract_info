"""Panel de filtros para la tabla de resultados."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FilterPanel(QWidget):
    """Panel con filtros para refinar la tabla de resultados."""

    filters_changed = Signal(dict)

    def __init__(self, parent=None, node_names: list[str] = None):
        super().__init__(parent)
        self._folder_combo: QComboBox
        self._estado_combo: QComboBox
        self._text_edit: QLineEdit
        self._clear_btn: QPushButton
        self._pipeline_combo: QComboBox

        self._node_names = node_names or []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Selector de pipeline
        layout.addWidget(QLabel("Pipeline:"))
        self._pipeline_combo = QComboBox()
        self._pipeline_combo.addItems(self._node_names if self._node_names else ["Retail", "Aseguradora"])
        self._pipeline_combo.setMinimumWidth(160)
        self._pipeline_combo.currentTextChanged.connect(self._emit_filters)
        layout.addWidget(self._pipeline_combo)

        # Filtro por carpeta
        layout.addWidget(QLabel("Carpeta:"))
        self._folder_combo = QComboBox()
        self._folder_combo.addItem("Todas")
        self._folder_combo.setMinimumWidth(180)
        self._folder_combo.currentTextChanged.connect(self._emit_filters)
        layout.addWidget(self._folder_combo)

        # Filtro por estado
        layout.addWidget(QLabel("Estado:"))
        self._estado_combo = QComboBox()
        self._estado_combo.addItems(["Todos", "EXITO", "ADVERTENCIA", "ERROR", "REVISAR"])
        self._estado_combo.setMinimumWidth(140)
        self._estado_combo.currentTextChanged.connect(self._emit_filters)
        layout.addWidget(self._estado_combo)

        # Filtro de texto libre
        layout.addWidget(QLabel("Buscar:"))
        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("Filtrar por texto...")
        self._text_edit.setClearButtonEnabled(True)
        self._text_edit.textChanged.connect(self._emit_filters)
        layout.addWidget(self._text_edit, stretch=1)

        # Botón limpiar
        self._clear_btn = QPushButton("Limpiar")
        self._clear_btn.clicked.connect(self.clear_filters)
        layout.addWidget(self._clear_btn)

    def update_folder_list(self, folders: list[str]) -> None:
        """Actualiza la lista de carpetas disponibles."""
        current = self._folder_combo.currentText()
        self._folder_combo.blockSignals(True)
        self._folder_combo.clear()
        self._folder_combo.addItem("Todas")
        self._folder_combo.addItems(sorted(folders))
        # Restaurar selección si existe
        idx = self._folder_combo.findText(current)
        if idx >= 0:
            self._folder_combo.setCurrentIndex(idx)
        self._folder_combo.blockSignals(False)

    def _emit_filters(self) -> None:
        self.filters_changed.emit(self.get_filters())

    def get_filters(self) -> dict:
        return {
            "pipeline": self._pipeline_combo.currentText(),
            "folder": self._folder_combo.currentText(),
            "estado": self._estado_combo.currentText(),
            "text": self._text_edit.text(),
        }

    def clear_filters(self) -> None:
        self._folder_combo.blockSignals(True)
        self._estado_combo.blockSignals(True)
        self._text_edit.blockSignals(True)
        self._pipeline_combo.blockSignals(True)

        self._folder_combo.setCurrentIndex(0)
        self._estado_combo.setCurrentIndex(0)
        self._text_edit.clear()
        self._pipeline_combo.setCurrentIndex(0)

        self._folder_combo.blockSignals(False)
        self._estado_combo.blockSignals(False)
        self._text_edit.blockSignals(False)
        self._pipeline_combo.blockSignals(False)

        self._emit_filters()