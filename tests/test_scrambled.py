"""Tests para layouts de 2 columnas (scrambled) en contratos de tarjeta de crédito."""

import os

import pytest

from extract_info.models import EstadoExtraccion
from extract_info.pipeline import process_pdf


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

SCRAMBLED_PDFS = [
    "101105644_37913856.pdf",
    "19116203K_37845508.pdf",
    "26536036K_37883492.pdf",
    "85638092_36644176.pdf",
    "95282253_38104198.pdf",
]

NORMAL_PDFS = [
    "101178358_28022378.pdf",
    "102722221_37750836.pdf",
]


@pytest.fixture(scope="module")
def sample_results():
    results = {}
    for fname in SCRAMBLED_PDFS + NORMAL_PDFS:
        path = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(path):
            results[fname] = process_pdf(path, "assets_test")
    return results


class TestScrambledLayout:
    """Tests para PDFs con layout de 2 columnas (scrambled)."""

    def test_nombre_completo_extracted(self, sample_results):
        """El nombre debe extraerse correctamente en layouts scrambled."""
        for fname in SCRAMBLED_PDFS:
            result = sample_results.get(fname)
            assert result is not None, f"PDF no procesado: {fname}"
            assert result.nombre_completo != "NO_EXTRAIDO", f"Nombre no extraído en {fname}"
            assert len(result.nombre_completo) > 2, f"Nombre muy corto en {fname}"

    def test_rut_extracted_from_name_block(self, sample_results):
        """El RUT debe extraerse del bloque combinado Nombre+RUT en layouts scrambled."""
        for fname in SCRAMBLED_PDFS:
            result = sample_results.get(fname)
            assert result is not None
            assert result.rut != "0.000.000-0", f"RUT no extraído en {fname}"
            # Verificar formato RUT válido
            import re
            assert re.match(r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$", result.rut), f"RUT formato inválido en {fname}: {result.rut}"

    def test_proto_repertorio_extracted(self, sample_results):
        """Proto y Repertorio deben extraerse del bloque de valores."""
        for fname in SCRAMBLED_PDFS + NORMAL_PDFS:
            result = sample_results.get(fname)
            assert result is not None
            assert result.proto > 1, f"Proto no extraído en {fname}"
            assert result.repertorio > 1, f"Repertorio no extraído en {fname}"
            assert result.fecha_repertorio != "00-00-0000", f"Fecha repertorio no extraída en {fname}"

    def test_normal_layout_still_works(self, sample_results):
        """Los layouts normales (una columna) deben seguir funcionando."""
        for fname in NORMAL_PDFS:
            result = sample_results.get(fname)
            assert result is not None
            assert result.estado_extraccion == EstadoExtraccion.EXITO, f"Normal falló: {fname} - {result.observaciones}"
            assert result.nombre_completo != "NO_EXTRAIDO"
            assert result.rut != "0.000.000-0"

    def test_fecha_contrato_normal(self, sample_results):
        """Fecha contrato debe extraerse en layouts normales."""
        for fname in NORMAL_PDFS:
            result = sample_results.get(fname)
            assert result is not None
            assert result.fecha_contrato != "00-00-0000", f"Fecha contrato no extraída en {fname}"


class TestScrambledSpecifics:
    """Tests específicos para verificar los datos en PDFs scrambled conocidos."""

    def test_101105644_data(self, sample_results):
        result = sample_results.get("101105644_37913856.pdf")
        assert result is not None
        assert "ELIZABETH DEL PILAR CALDERON LEAL" in result.nombre_completo
        assert result.rut == "10.110.564-4"
        assert result.proto == 111746
        assert result.repertorio == 61004
        assert result.fecha_repertorio == "24-07-2026"

    def test_19116203K_data(self, sample_results):
        result = sample_results.get("19116203K_37845508.pdf")
        assert result is not None
        assert "NATALIA EDITH CAVIEDES BORBALAN" in result.nombre_completo
        assert result.rut == "19.116.203-K"
        assert result.proto == 111818

    def test_26536036K_data(self, sample_results):
        result = sample_results.get("26536036K_37883492.pdf")
        assert result is not None
        assert "JORGE ERNESTO ORTIZ ORDINOLA" in result.nombre_completo
        assert result.rut == "26.536.036-K"

    def test_85638092_data(self, sample_results):
        result = sample_results.get("85638092_36644176.pdf")
        assert result is not None
        assert "RODOLFO ALEXIS SIERRALTA SALINAS" in result.nombre_completo
        assert result.rut == "8.563.809-2"

    def test_95282253_data(self, sample_results):
        result = sample_results.get("95282253_38104198.pdf")
        assert result is not None
        assert "DANIEL HERNAN VALLEJOS PEDREROS" in result.nombre_completo
        assert result.rut == "9.528.225-3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])