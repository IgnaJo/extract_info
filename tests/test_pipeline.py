"""Tests para el pipeline de extracción."""

import os

import fitz
import pytest

from extract_info.models import EstadoExtraccion
from extract_info.pipeline import process_pdf


def _create_test_pdf(text_per_page: list[str], path: str) -> None:
    """Crea un PDF de prueba."""
    doc = fitz.open()
    for text in text_per_page:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


@pytest.fixture
def pdf_ok(tmp_path):
    """PDF con todos los campos presentes (formato contrato tarjeta)."""
    path = str(tmp_path / "ok.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 100), "Nombre Completo:")
    page.insert_text((40, 115), "Juan Pérez González")
    page.insert_text((40, 130), "RUT: 12.345.678-5")
    page.insert_text((335, 30), "PROTOCOLIZADO N°")
    page.insert_text((335, 45), "REP N°                                DE")
    page.insert_text((343, 25), "12345")
    page.insert_text((343, 40), "6789        25-06-2024")
    page.insert_text((40, 500), "Plan de Cobros Vigentes al 25/06/2024")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def pdf_missing_fields(tmp_path):
    """PDF con campos faltantes."""
    path = str(tmp_path / "missing.pdf")
    pages = [
        "PROTOCOLIZADO N° 12345",
        "Sin datos relevantes.",
        "Sin nombre ni RUT aquí.",
    ]
    _create_test_pdf(pages, path)
    return path


class TestProcessPdf:
    def test_ok_extraction(self, pdf_ok):
        result = process_pdf(pdf_ok, "carpeta_test")
        assert result.nombre_archivo == "ok.pdf"
        assert result.nombre_carpeta == "carpeta_test"
        assert result.nombre_completo == "Juan Pérez González"
        assert result.rut == "12.345.678-5"
        assert result.fecha_contrato == "25-06-2024"

    def test_missing_fields(self, pdf_missing_fields):
        result = process_pdf(pdf_missing_fields, "carpeta_test")
        assert result.estado_extraccion == EstadoExtraccion.ADVERTENCIA

    def test_nonexistent_file(self):
        result = process_pdf("/nonexistent/file.pdf", "carpeta_test")
        assert result.estado_extraccion == EstadoExtraccion.ERROR

    def test_metadata(self, pdf_ok):
        result = process_pdf(pdf_ok, "carpeta_test")
        assert result.nombre_archivo == "ok.pdf"
