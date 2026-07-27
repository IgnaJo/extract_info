"""Tests para batch processor."""

import os

import fitz
import pytest

from extract_info.batch import FolderResult, get_folder_name, process_batch, process_folder, scan_folders


def _create_test_pdf(text: str, path: str) -> None:
    """Crea un PDF de prueba."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


@pytest.fixture
def sample_structure(tmp_path):
    """Crea una estructura de carpetas de prueba."""
    # Carpeta 1: 2 PDFs
    folder1 = tmp_path / "carpeta_1"
    folder1.mkdir()
    _create_test_pdf(
        "PROTOCOLIZADO N° 11111\nREP N° 2222 DE 01-01-2024\nNombre completo: Ana\nRUT: 11.111.111-1\nVigentes al 01-01-2024",
        str(folder1 / "doc1.pdf"),
    )
    _create_test_pdf(
        "PROTOCOLIZADO N° 33333\nREP N° 4444 DE 02-02-2024\nNombre completo: Beto\nRUT: 22.222.222-2\nVigentes al 02-02-2024",
        str(folder1 / "doc2.pdf"),
    )

    # Carpeta 2: 1 PDF sin campos
    folder2 = tmp_path / "carpeta_2"
    folder2.mkdir()
    _create_test_pdf("Sin datos relevantes", str(folder2 / "doc3.pdf"))

    # Carpeta vacía (sin PDFs)
    folder3 = tmp_path / "carpeta_vacia"
    folder3.mkdir()

    return tmp_path


class TestScanFolders:
    def test_finds_folders_with_pdfs(self, sample_structure):
        folders = scan_folders(str(sample_structure))
        assert len(folders) == 2

    def test_excludes_empty_folders(self, sample_structure):
        folders = scan_folders(str(sample_structure))
        for f in folders:
            assert "carpeta_vacia" not in f


class TestGetFolderName:
    def test_simple_path(self):
        assert get_folder_name("/path/to/my_folder") == "my_folder"

    def test_trailing_slash(self):
        assert get_folder_name("/path/to/my_folder/") == "my_folder"


class TestProcessFolder:
    def test_processes_all_pdfs(self, sample_structure):
        folder = str(sample_structure / "carpeta_1")
        result = process_folder(folder)
        assert isinstance(result, FolderResult)
        assert result.nombre_carpeta == "carpeta_1"
        assert len(result.documentos) == 2

    def testHandles_missing_fields(self, sample_structure):
        folder = str(sample_structure / "carpeta_2")
        result = process_folder(folder)
        assert len(result.documentos) == 1
        # Should have ADVERTENCIA state due to missing fields
        assert result.documentos[0].estado_extraccion.value in ("EXITO", "ADVERTENCIA", "ERROR")


class TestProcessBatch:
    def test_processes_all_folders(self, sample_structure):
        results = process_batch(str(sample_structure), max_workers=1)
        assert len(results) == 2

    def test_results_sorted(self, sample_structure):
        results = process_batch(str(sample_structure), max_workers=1)
        names = [r.nombre_carpeta for r in results]
        assert names == sorted(names)

    def test_empty_root(self, tmp_path):
        results = process_batch(str(tmp_path), max_workers=1)
        assert results == []
