"""Tabla de resultados con modelo, proxy para ordenar/filtrar y delegate para estados."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)


HEADER_LABELS = {
    "nombre_archivo": "Archivo",
    "nombre_completo": "Nombre Completo",
    "rut": "RUT",
    "fecha_contrato": "Fecha Contrato",
    "proto": "Nº Proto",
    "repertorio": "Repertorio",
    "fecha_repertorio": "Fecha Repertorio",
    "cantidad_hojas": "Hojas",
    "nombre_carpeta": "Carpeta",
    "estado_extraccion": "Estado",
    "observaciones": "Observaciones",
    "Nombre Firmante": "Nombre",
    "PROTOCOLIZADO Nº": "Nº Proto",
    "Cantidad de páginas": "Hojas",
}


def display_label(column: str) -> str:
    """Etiqueta legible para la UI; las columnas del CSV no se tocan."""

    return HEADER_LABELS.get(column, column)


def configure_headers(table: QTableView) -> None:
    """Encabezados legibles por defecto y ajustados al contenido.

    ``ResizeToContents`` recalcula el ancho al cambiar los datos, así que el
    header completo nunca queda recortado; ``maximumSectionSize`` evita que una
    columna con textos largos (observaciones) se coma la tabla.
    """

    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setMaximumSectionSize(320)
    header.setStretchLastSection(True)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


class ResultTableModel(QAbstractTableModel):
    """Modelo de tabla para resultados de extracción."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns: list[str] = []
        self._rows: list[dict] = []

    def set_columns(self, columns: list[str]) -> None:
        self.beginResetModel()
        self._columns = columns
        self.endResetModel()

    def set_data(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col_name = self._columns[index.column()]
        value = row.get(col_name, "")

        if role == Qt.ItemDataRole.DisplayRole:
            return str(value) if value is not None else ""

        if role == Qt.ItemDataRole.ToolTipRole:
            return str(value) if value is not None else ""

        if role == Qt.ItemDataRole.UserRole:
            # Devolver la fila completa para el delegate de estados
            return row

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._columns):
                column = self._columns[section]
                if role == Qt.ItemDataRole.DisplayRole:
                    return display_label(column)
                if role == Qt.ItemDataRole.ToolTipRole:
                    return column
        return None

    def get_row_data(self, row: int) -> dict:
        if 0 <= row < len(self._rows):
            return self._rows[row].copy()
        return {}


class ResultSortFilterProxyModel(QSortFilterProxyModel):
    """Proxy model que filtra y ordena, y expone el estado por fila."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_folder: str = ""
        self._filter_estado: str = ""
        self._filter_text: str = ""

    def set_folder_filter(self, folder: str) -> None:
        self._filter_folder = folder
        self.invalidateFilter()

    def set_estado_filter(self, estado: str) -> None:
        self._filter_estado = estado
        self.invalidateFilter()

    def set_text_filter(self, text: str) -> None:
        self._filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if not isinstance(model, ResultTableModel):
            return True

        row_data = model.get_row_data(source_row)

        # Filtro por carpeta
        if self._filter_folder and self._filter_folder != "Todas":
            folder_value = str(row_data.get("nombre_carpeta", ""))
            if folder_value != self._filter_folder:
                return False

        # Filtro por estado
        if self._filter_estado and self._filter_estado != "Todos":
            estado_value = str(
                row_data.get("Estado", row_data.get("estado_extraccion", ""))
            )
            if self._filter_estado not in estado_value:
                return False

        # Filtro de texto libre
        if self._filter_text:
            match = False
            for value in row_data.values():
                if self._filter_text in str(value).lower():
                    match = True
                    break
            if not match:
                return False

        return True


class ResultRowDelegate(QStyledItemDelegate):
    """Delegate que colorea filas según estado (EXITO/ADVERTENCIA/ERROR).

    Usa colores definidos en QSS (assets/styles/style.QSS).
    """

    def paint(
        self,
        painter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        row_data = index.data(Qt.ItemDataRole.UserRole)
        if not row_data:
            super().paint(painter, option, index)
            return

        estado = str(row_data.get("Estado", row_data.get("estado_extraccion", ""))).upper()

        # Poner propiedad de estado en la opción para que QSS pueda usarla
        if "OK" in estado or "EXITO" in estado:
            option.property("rowStatus", "exito")
        elif "REVISAR" in estado or "ADVERTENCIA" in estado or "WARNING" in estado:
            option.property("rowStatus", "advertencia")
        elif "ERROR" in estado:
            option.property("rowStatus", "error")
        else:
            super().paint(painter, option, index)
            return

        super().paint(painter, option, index)