"""Tabla de resultados con modelo y proxy para ordenar/filtrar."""

from __future__ import annotations

from typing import Any, Sequence

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtWidgets import QHeaderView, QTableView

from extract_info.columns import ColumnKind, ColumnSpec, column_keys, find_kind


def _coerce_column(column: ColumnSpec | str) -> ColumnSpec:
    """Acepta ColumnSpec o el nombre plano (tests y compatibilidad)."""

    return column if isinstance(column, ColumnSpec) else ColumnSpec(key=column, label=column)


_BASE_MAX_SECTION_WIDTH = 320


def _maximum_section_size(table: QTableView, columns: Sequence[ColumnSpec | str] | None) -> int:
    """Tope de ancho que nunca recorta un header completo.

    ``maximumSectionSize`` limita el ancho calculado para el contenido, pero
    también recortaría el label del header si fuese más ancho. Se parte de 320
    (evita que ``Observaciones`` se coma la tabla) y se sube al ancho del label
    más largo, que varía según la fuente/DPI del sistema.
    """

    if not columns:
        return _BASE_MAX_SECTION_WIDTH
    fm = table.horizontalHeader().fontMetrics()
    widest = max(
        fm.horizontalAdvance(_coerce_column(column).label.upper()) for column in columns
    )
    return max(_BASE_MAX_SECTION_WIDTH, widest + 24)


def configure_headers(
    table: QTableView, columns: Sequence[ColumnSpec | str] | None = None
) -> None:
    """Encabezados legibles por defecto y ajustados al contenido.

    ``ResizeToContents`` recalcula el ancho al cambiar los datos, así que el
    header completo nunca queda recortado; ``maximumSectionSize`` evita que una
    columna con textos largos (observaciones) se coma la tabla, sin recortar
    nunca el label del header.
    """

    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setMaximumSectionSize(_maximum_section_size(table, columns))
    header.setStretchLastSection(True)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


class ResultTableModel(QAbstractTableModel):
    """Modelo de tabla para resultados de extracción."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._specs: list[ColumnSpec] = []
        self._columns: list[str] = []
        self._rows: list[dict] = []

    def set_columns(self, columns: list[ColumnSpec | str]) -> None:
        self.beginResetModel()
        self._specs = [_coerce_column(column) for column in columns]
        self._columns = column_keys(self._specs)
        self.endResetModel()

    @property
    def status_key(self) -> str | None:
        """Clave de la columna de estado, si el esquema la declara."""

        spec = find_kind(self._specs, ColumnKind.STATUS)
        return spec.key if spec else None

    @property
    def folder_key(self) -> str | None:
        """Clave de la columna de carpeta, si el esquema la declara."""

        spec = find_kind(self._specs, ColumnKind.FOLDER)
        return spec.key if spec else None

    def set_data(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
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

    def headerData(  # noqa: N802 - override de Qt
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._specs):
                spec = self._specs[section]
                if role == Qt.ItemDataRole.DisplayRole:
                    # Norma de presentación: encabezados en mayúsculas. El CSV
                    # conserva las claves canónicas (``spec.key``).
                    return spec.label.upper()
                if role == Qt.ItemDataRole.ToolTipRole:
                    return spec.key
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

    def filterAcceptsRow(  # noqa: N802 - override de Qt
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        model = self.sourceModel()
        if not isinstance(model, ResultTableModel):
            return True

        row_data = model.get_row_data(source_row)

        # Filtro por carpeta (columna declarada, con fallback legacy)
        if self._filter_folder and self._filter_folder != "Todas":
            folder_key = model.folder_key or "nombre_carpeta"
            folder_value = str(row_data.get(folder_key, ""))
            if folder_value != self._filter_folder:
                return False

        # Filtro por estado (columna declarada, con fallback legacy)
        if self._filter_estado and self._filter_estado != "Todos":
            status_key = model.status_key
            if status_key is None:
                status_key = "Estado" if "Estado" in row_data else "estado_extraccion"
            estado_value = str(row_data.get(status_key, ""))
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
