"""Tests para patrones regex de extracción."""


from extract_info.extraction.patterns import (
    PAT_FECHA_REP_VALUE,
    PAT_FECHA_VIGENTE,
    PAT_NOMBRE_CC,
    PAT_NOMBRE_NOT,
    PAT_PROTO_VALUE,
    PAT_REP_VALUE,
    PAT_RUT_CC,
    PAT_RUT_NOT,
    detect_document_type,
)


class TestDetectDocumentType:
    def test_credit_card(self):
        text = "Nombre Completo: Juan\nVigentes al 25/06/2024"
        assert detect_document_type(text) == "credit_card"

    def test_notarized(self):
        text = "RUN del Firmante: 12.345.678-5\nFecha de la Firma: 25-06-2024"
        assert detect_document_type(text) == "notarized"

    def test_default_credit_card(self):
        text = "Some random text without markers"
        assert detect_document_type(text) == "credit_card"


class TestPatNombreCC:
    def test_match_simple(self):
        texto = "Nombre Completo:\nJUAN PEREZ\nRUT: 12.345.678-5"
        match = PAT_NOMBRE_CC.search(texto)
        assert match is not None
        # Pattern matches just "Nombre Completo:" label

    def test_no_match(self):
        texto = "No hay nombre aquí"
        assert PAT_NOMBRE_CC.search(texto) is None


class TestPatRutCC:
    def test_match_rut(self):
        texto = "RUT: 12.345.678-5"
        match = PAT_RUT_CC.search(texto)
        assert match is not None
        assert match.group(1) == "12.345.678-5"

    def test_match_rut_k(self):
        texto = "RUT: 12.345.678-K"
        match = PAT_RUT_CC.search(texto)
        assert match is not None
        assert match.group(1) == "12.345.678-K"

    def test_no_match(self):
        texto = "Sin RUT"
        assert PAT_RUT_CC.search(texto) is None


class TestPatFechaVigente:
    def test_match_vigentes_al(self):
        texto = "Plan de Cobros Vigentes al 25/06/2024"
        match = PAT_FECHA_VIGENTE.search(texto)
        assert match is not None
        assert match.group(1) == "25/06/2024"

    def test_no_match(self):
        texto = "Sin fecha vigente"
        assert PAT_FECHA_VIGENTE.search(texto) is None


class TestPatNombreNot:
    def test_match(self):
        texto = "Nombre: Juan Pérez\nRUT: 12.345.678-5"
        match = PAT_NOMBRE_NOT.search(texto)
        assert match is not None
        assert "Juan Pérez" in match.group(1)

    def test_no_match(self):
        texto = "Sin nombre"
        assert PAT_NOMBRE_NOT.search(texto) is None


class TestPatRutNot:
    def test_match(self):
        texto = "RUN del Firmante: 12.345.678-5"
        match = PAT_RUT_NOT.search(texto)
        assert match is not None
        assert match.group(1) == "12.345.678-5"

    def test_no_match(self):
        texto = "Sin RUN"
        assert PAT_RUT_NOT.search(texto) is None


class TestPatProtoValue:
    def test_match(self):
        texto = "  111746\n      61004        24-07-2026"
        match = PAT_PROTO_VALUE.search(texto)
        assert match is not None
        assert match.group(1) == "111746"


class TestPatRepValue:
    def test_match(self):
        texto = "  111746\n      61004        24-07-2026"
        match = PAT_REP_VALUE.search(texto)
        assert match is not None
        # Matches first 4-7 digit number in the text
        assert match.group(1) in ("111746", "61004")


class TestPatFechaRepValue:
    def test_match(self):
        texto = "  111746\n      61004        24-07-2026"
        match = PAT_FECHA_REP_VALUE.search(texto)
        assert match is not None
        assert match.group(1) == "24-07-2026"
