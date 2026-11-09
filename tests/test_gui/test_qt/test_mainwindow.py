"""Tests pytest-qt para MainWindow."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from extract_info.gui.app import MainWindow
from extract_info.pipelines.base import list_nodes


@pytest.fixture(scope="session")
def qapp():
    """Fixture para QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_mainwindow_opens(qapp):
    """MainWindow se abre sin errores."""
    window = MainWindow()
    window.show()
    assert window.isVisible()
    window.close()


def test_mainwindow_has_expected_widgets(qapp):
    """MainWindow tiene los widgets esperados."""
    window = MainWindow()
    window.show()

    # Verificar widgets principales
    assert window.drop_zone is not None
    assert window.filter_panel is not None
    assert window.log_viewer is not None
    assert window._table_view is not None
    assert window._table_model is not None
    assert window._proxy_model is not None
    assert window.progress_bar is not None
    assert window._legend_widget is not None

    # Verificar botones
    assert window.btn_run is not None
    assert window.btn_pause is not None
    assert window.btn_cancel is not None
    assert window.btn_export is not None

    # Verificar combo de nodos
    assert window.combo_node is not None
    assert window.combo_node.count() >= 2  # Retail, Aseguradora

    window.close()


def test_node_selector_changes_model(qapp):
    """Cambiar de nodo actualiza las columnas del modelo."""
    window = MainWindow()
    window.show()

    # Procesar eventos para que el combo inicial cargue el nodo
    qapp.processEvents()

    # Nodo inicial (Aseguradora por orden alfabético)
    initial_columns = window._table_model._columns
    assert "Archivo" in initial_columns
    assert "RUN Firmante" in initial_columns

    # Cambiar a Retail
    window.combo_node.setCurrentText("Retail")
    qapp.processEvents()

    retail_columns = window._table_model._columns
    assert "nombre_archivo" in retail_columns
    assert "rut" in retail_columns

    window.close()


def test_shortcuts_registered(qapp):
    """Atajos F5 y Escape están registrados."""
    from PySide6.QtGui import QShortcut

    window = MainWindow()
    window.show()

    # Verificar que existen shortcuts
    shortcuts = window.findChildren(QShortcut)
    assert len(shortcuts) >= 2  # F5 y Escape

    window.close()


def test_window_icon_set(qapp):
    """Icono de ventana está configurado."""
    window = MainWindow()
    assert not window.windowIcon().isNull()
    window.close()


def test_statusbar_has_progress_and_legend(qapp):
    """Statusbar tiene barra de progreso y leyenda."""
    window = MainWindow()
    window.show()

    assert window.progress_bar is not None
    assert window._legend_widget is not None
    # Verificar que la leyenda tiene los 3 estados
    legend_text = window._legend_widget.findChildren(QLabel)
    assert len(legend_text) >= 4  # "Estados:" + 3 estados

    window.close()


def test_table_headers_are_responsive_and_readable(qapp):
    """Los headers se ajustan al contenido y su etiqueta completa se lee por defecto."""
    from PySide6.QtWidgets import QHeaderView

    window = MainWindow()
    window.show()
    table = window._table_view
    header = table.horizontalHeader()
    fm = header.fontMetrics()

    for node in list_nodes():
        window.combo_node.setCurrentText(node)
        model = table.model()
        assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.ResizeToContents
        for col in range(model.columnCount()):
            label = str(model.headerData(col, Qt.Orientation.Horizontal))
            assert table.columnWidth(col) >= fm.horizontalAdvance(label), (
                f"{node}: columna {col!r} corta para su header"
            )

    window.close()


def test_table_shows_display_labels_but_keeps_csv_keys(qapp):
    """La tabla muestra etiquetas cortas; debajo las columnas siguen siendo las del CSV."""
    window = MainWindow()
    window.show()

    window.combo_node.setCurrentText("Retail")
    model = window._table_model
    assert model._columns[1] == "nombre_completo"
    labels = [model.headerData(c, Qt.Orientation.Horizontal) for c in range(4)]
    assert labels == ["Archivo", "Nombre Completo", "RUT", "Fecha Contrato"]

    window.combo_node.setCurrentText("Aseguradora")
    model = window._table_model
    assert model._columns[5] == "PROTOCOLIZADO Nº"
    assert model.headerData(5, Qt.Orientation.Horizontal) == "Nº Proto"

    window.close()
