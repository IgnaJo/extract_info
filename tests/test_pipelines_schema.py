"""Tests del esquema declarativo de columnas y su uso en process_folder."""

from __future__ import annotations

from extract_info.columns import ColumnKind, ColumnSpec, find_kind
from extract_info.extraction import file_discovery
from extract_info.pipelines.base import NODE_SPECS, _create_error_row, process_folder


def test_node_specs_declare_semantic_kinds():
    retail = NODE_SPECS["Retail"]["columns"]
    assert find_kind(retail, ColumnKind.FILENAME).key == "nombre_archivo"
    assert find_kind(retail, ColumnKind.STATUS).key == "estado_extraccion"
    assert find_kind(retail, ColumnKind.FOLDER).key == "nombre_carpeta"
    assert find_kind(retail, ColumnKind.NUMBER).label == "Hojas"

    # csv_columns sigue derivándose del esquema.
    assert NODE_SPECS["Retail"]["csv_columns"] == [c.key for c in retail]


def test_error_row_uses_kind_not_column_name():
    columns = NODE_SPECS["Aseguradora"]["columns"]
    row = _create_error_row("doc.pdf", "boom", columns)

    assert row["Archivo"] == "doc.pdf"
    assert row["Estado"] == "ERROR: boom"
    assert row["Cantidad de páginas"] == 0
    assert row["Fecha Firma"] is None
    # Una columna de texto con nombre engañoso no se toca.
    assert row["RUN Firmante"] is None


def test_process_folder_rejects_undeclared_columns(monkeypatch):
    monkeypatch.setattr(
        file_discovery,
        "discover_pdf_files",
        lambda root: [file_discovery.DiscoveredFile(path="x.pdf", relative_path="x.pdf")],
    )
    columns = (ColumnSpec("nombre_archivo", "Archivo", ColumnKind.FILENAME),
               ColumnSpec("estado_extraccion", "Estado", ColumnKind.STATUS))

    result = process_folder(
        folder_path="/tmp",
        process_single=lambda path: {"nombre_archivo": "x.pdf", "fantasma": 1},
        node_name="Test",
        columns=columns,
    )

    assert result.error_count == 1
    assert result.rows[0]["nombre_archivo"] == "x.pdf"
    assert "columnas no declaradas" in result.rows[0]["estado_extraccion"]
    assert "fantasma" not in result.rows[0]
