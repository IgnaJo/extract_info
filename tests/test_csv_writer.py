"""Tests para CSV writer."""

import os

import pandas as pd
import pytest

from extract_info.batch import FolderResult
from extract_info.csv_writer import CSV_COLUMNS, write_all_csvs, write_folder_csv
from extract_info.models import ContratoSchema, EstadoExtraccion


def _make_doc(**overrides) -> ContratoSchema:
    base = dict(
        nombre_completo="Test User",
        rut="12.345.678-5",
        fecha_contrato="25-06-2024",
        proto=12345,
        repertorio=6789,
        fecha_repertorio="20-06-2024",
        nombre_archivo="test.pdf",
        cantidad_hojas=5,
        nombre_carpeta="carpeta_test",
        estado_extraccion=EstadoExtraccion.EXITO,
        observaciones="",
    )
    base.update(overrides)
    return ContratoSchema(**base)


@pytest.fixture
def sample_result():
    return FolderResult(
        nombre_carpeta="carpeta_1",
        ruta_carpeta="/tmp/carpeta_1",
        documentos=[
            _make_doc(nombre_archivo="doc1.pdf"),
            _make_doc(
                nombre_archivo="doc2.pdf",
                estado_extraccion=EstadoExtraccion.ADVERTENCIA,
                observaciones="Campos faltantes",
            ),
        ],
    )


@pytest.fixture
def empty_result():
    return FolderResult(
        nombre_carpeta="carpeta_vacia",
        ruta_carpeta="/tmp/carpeta_vacia",
        documentos=[],
    )


class TestWriteFolderCsv:
    def test_creates_csv(self, sample_result, tmp_path):
        path = write_folder_csv(sample_result, str(tmp_path))
        assert os.path.exists(path)
        assert path.endswith(".csv")

    def test_csv_has_correct_columns(self, sample_result, tmp_path):
        path = write_folder_csv(sample_result, str(tmp_path))
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert list(df.columns) == CSV_COLUMNS

    def test_csv_has_correct_row_count(self, sample_result, tmp_path):
        path = write_folder_csv(sample_result, str(tmp_path))
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert len(df) == 2

    def test_csv_filename_format(self, sample_result, tmp_path):
        path = write_folder_csv(sample_result, str(tmp_path))
        assert "resultado_carpeta_1.csv" in path

    def test_csv_content(self, sample_result, tmp_path):
        path = write_folder_csv(sample_result, str(tmp_path))
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert df.iloc[0]["nombre_archivo"] == "doc1.pdf"
        assert df.iloc[1]["estado_extraccion"] == "ADVERTENCIA"


class TestWriteAllCsvs:
    def test_writes_multiple_csvs(self, sample_result, tmp_path):
        results = [sample_result]
        paths = write_all_csvs(results, str(tmp_path))
        assert len(paths) == 1
        assert os.path.exists(paths[0])

    def test_skips_empty_folders(self, empty_result, tmp_path):
        paths = write_all_csvs([empty_result], str(tmp_path))
        assert paths == []

    def test_creates_output_dir(self, sample_result, tmp_path):
        output = tmp_path / "new_dir"
        write_all_csvs([sample_result], str(output))
        assert output.exists()


def test_none_values_become_empty_cells(tmp_path):
    """Un campo no extraído sale como celda vacía, no como centinela."""
    import csv

    result = FolderResult(
        nombre_carpeta="carpeta_none",
        ruta_carpeta="/tmp/carpeta_none",
        documentos=[_make_doc(
            nombre_archivo="doc.pdf", nombre_completo=None, rut=None,
            fecha_contrato=None, proto=None, repertorio=None,
            fecha_repertorio=None, cantidad_hojas=None,
        )],
    )

    path = write_folder_csv(result, str(tmp_path))

    with open(path, encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    for column in ("nombre_completo", "rut", "fecha_contrato", "proto",
                   "repertorio", "fecha_repertorio", "cantidad_hojas"):
        assert row[column] == "", f"{column} debería quedar vacío: {row[column]!r}"


RETAIL_CSV_COLUMNS = [
    "nombre_archivo",
    "nombre_completo",
    "rut",
    "fecha_contrato",
    "proto",
    "repertorio",
    "fecha_repertorio",
    "cantidad_hojas",
    "nombre_carpeta",
    "estado_extraccion",
    "observaciones",
]

ASEGURADORA_CSV_COLUMNS = [
    "Archivo",
    "Fecha Firma",
    "RUN Firmante",
    "Nombre Firmante",
    "REP Nº",
    "PROTOCOLIZADO Nº",
    "REP Fecha",
    "Cantidad de páginas",
    "Estado",
]


def test_retail_csv_headers_are_canonical():
    """Los headers del CSV Retail son contrato con la base general: no se renombran."""
    from extract_info.pipelines.base import get_node_spec

    assert CSV_COLUMNS == RETAIL_CSV_COLUMNS
    assert get_node_spec("Retail")["csv_columns"] == RETAIL_CSV_COLUMNS


def test_aseguradora_csv_headers_are_canonical():
    """Los headers del CSV Aseguradora tampoco cambian por estética de UI."""
    from extract_info.pipelines.base import get_node_spec

    assert get_node_spec("Aseguradora")["csv_columns"] == ASEGURADORA_CSV_COLUMNS
