"""Tests pytest-qt para modelo y proxy de tabla."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from extract_info.gui.widgets.results_table import (
    ResultSortFilterProxyModel,
    ResultTableModel,
)


@pytest.fixture(scope="session")
def qapp():
    """Fixture para QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_model_set_columns(qapp):
    """Modelo acepta y expone columnas."""
    model = ResultTableModel()
    model.set_columns(["col1", "col2", "col3"])

    assert model.columnCount() == 3
    assert model.headerData(0, Qt.Orientation.Horizontal) == "col1"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "col2"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "col3"


def test_model_set_data(qapp):
    """Modelo acepta y expone filas de datos."""
    model = ResultTableModel()
    model.set_columns(["nombre", "valor"])
    model.set_data([
        {"nombre": "a", "valor": 1},
        {"nombre": "b", "valor": 2},
    ])

    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "a"
    assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "1"
    assert model.data(model.index(1, 0), Qt.ItemDataRole.DisplayRole) == "b"
    assert model.data(model.index(1, 1), Qt.ItemDataRole.DisplayRole) == "2"


def test_model_user_role_returns_full_row(qapp):
    """UserRole devuelve la fila completa para delegate."""
    model = ResultTableModel()
    model.set_columns(["nombre", "estado"])
    model.set_data([{"nombre": "test.pdf", "estado": "EXITO"}])

    row_data = model.data(model.index(0, 0), Qt.ItemDataRole.UserRole)
    assert row_data == {"nombre": "test.pdf", "estado": "EXITO"}


def test_proxy_model_sort(qapp):
    """Proxy model ordena correctamente."""
    model = ResultTableModel()
    model.set_columns(["nombre", "valor"])
    model.set_data([
        {"nombre": "c", "valor": 3},
        {"nombre": "a", "valor": 1},
        {"nombre": "b", "valor": 2},
    ])

    proxy = ResultSortFilterProxyModel()
    proxy.setSourceModel(model)
    proxy.sort(0, Qt.SortOrder.AscendingOrder)

    assert proxy.rowCount() == 3
    assert proxy.data(proxy.index(0, 0)) == "a"
    assert proxy.data(proxy.index(1, 0)) == "b"
    assert proxy.data(proxy.index(2, 0)) == "c"


def test_proxy_model_filter_folder(qapp):
    """Proxy model filtra por carpeta."""
    model = ResultTableModel()
    model.set_columns(["nombre", "nombre_carpeta"])
    model.set_data([
        {"nombre": "a.pdf", "nombre_carpeta": "Carpeta1"},
        {"nombre": "b.pdf", "nombre_carpeta": "Carpeta2"},
        {"nombre": "c.pdf", "nombre_carpeta": "Carpeta1"},
    ])

    proxy = ResultSortFilterProxyModel()
    proxy.setSourceModel(model)

    # Sin filtro
    assert proxy.rowCount() == 3

    # Filtrar Carpeta1
    proxy.set_folder_filter("Carpeta1")
    assert proxy.rowCount() == 2
    assert proxy.data(proxy.index(0, 0)) == "a.pdf"
    assert proxy.data(proxy.index(1, 0)) == "c.pdf"

    # Filtrar Carpeta2
    proxy.set_folder_filter("Carpeta2")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 0)) == "b.pdf"

    # Restaurar todas
    proxy.set_folder_filter("Todas")
    assert proxy.rowCount() == 3


def test_proxy_model_filter_estado(qapp):
    """Proxy model filtra por estado."""
    model = ResultTableModel()
    model.set_columns(["nombre", "Estado"])
    model.set_data([
        {"nombre": "a.pdf", "Estado": "EXITO"},
        {"nombre": "b.pdf", "Estado": "ADVERTENCIA"},
        {"nombre": "c.pdf", "Estado": "ERROR"},
    ])

    proxy = ResultSortFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.set_estado_filter("EXITO")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 0)) == "a.pdf"

    proxy.set_estado_filter("ADVERTENCIA")
    assert proxy.rowCount() == 1

    proxy.set_estado_filter("Todos")
    assert proxy.rowCount() == 3


def test_proxy_model_filter_text(qapp):
    """Proxy model filtra por texto libre."""
    model = ResultTableModel()
    model.set_columns(["nombre", "rut"])
    model.set_data([
        {"nombre": "doc1.pdf", "rut": "12.345.678-9"},
        {"nombre": "doc2.pdf", "rut": "98.765.432-1"},
    ])

    proxy = ResultSortFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.set_text_filter("12.345")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 0)) == "doc1.pdf"

    proxy.set_text_filter("doc")
    assert proxy.rowCount() == 2

    proxy.set_text_filter("noexiste")
    assert proxy.rowCount() == 0
