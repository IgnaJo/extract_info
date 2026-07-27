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
            _make_doc(nombre_archivo="doc2.pdf", estado_extraccion=EstadoExtraccion.ADVERTENCIA, observaciones="Campos faltantes"),
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
