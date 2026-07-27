"""Tests para extracción con documentos de prueba (assets/)."""

import os

import pytest

from extract_info.models import EstadoExtraccion
from extract_info.pipeline import process_pdf


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

ASSET_PDFS = [
    "101105644_37913856.pdf",
    "102722221_37750836.pdf",
    "19116203K_37845508.pdf",
    "26536036K_37883492.pdf",
    "85638092_36644176.pdf",
    "95282253_38104198.pdf",
]


@pytest.fixture(scope="module")
def sample_results():
    results = {}
    for fname in ASSET_PDFS:
        path = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(path):
            results[fname] = process_pdf(path, "assets_test")
    return results


class TestCreditCardExtraction:
    def test_all_extracted(self, sample_results):
        for fname, result in sample_results.items():
            assert result.estado_extraccion == EstadoExtraccion.EXITO, f"{fname}: {result.observaciones}"

    def test_nombre_completo(self, sample_results):
        expected = {
            "101105644_37913856.pdf": "ELIZABETH DEL PILAR CALDERON LEAL",
            "102722221_37750836.pdf": "RUBEN LABRA LAGOS",
            "19116203K_37845508.pdf": "NATALIA EDITH CAVIEDES BORBALAN",
            "26536036K_37883492.pdf": "JORGE ERNESTO ORTIZ ORDINOLA",
            "85638092_36644176.pdf": "RODOLFO ALEXIS SIERRALTA SALINAS",
            "95282253_38104198.pdf": "DANIEL HERNAN VALLEJOS PEDREROS",
        }
        for fname, result in sample_results.items():
            assert result.nombre_completo == expected[fname], f"{fname}: {result.nombre_completo}"

    def test_rut(self, sample_results):
        expected = {
            "101105644_37913856.pdf": "10.110.564-4",
            "102722221_37750836.pdf": "10.272.222-1",
            "19116203K_37845508.pdf": "19.116.203-K",
            "26536036K_37883492.pdf": "26.536.036-K",
            "85638092_36644176.pdf": "8.563.809-2",
            "95282253_38104198.pdf": "9.528.225-3",
        }
        for fname, result in sample_results.items():
            assert result.rut == expected[fname], f"{fname}: {result.rut}"

    def test_proto(self, sample_results):
        for fname, result in sample_results.items():
            assert result.proto > 1, f"{fname}: proto={result.proto}"

    def test_repertorio(self, sample_results):
        for fname, result in sample_results.items():
            assert result.repertorio > 1, f"{fname}: rep={result.repertorio}"

    def test_fecha_repertorio(self, sample_results):
        for fname, result in sample_results.items():
            assert result.fecha_repertorio != "00-00-0000", f"{fname}: fecha_rep={result.fecha_repertorio}"

    def test_fecha_contrato(self, sample_results):
        for fname, result in sample_results.items():
            assert result.fecha_contrato != "00-00-0000", f"{fname}: fecha={result.fecha_contrato}"
