"""Tests para field validators."""

import pytest

from extract_info.extraction.validators import (
    validate_campos,
    validate_fecha,
    validate_numero,
    validate_paginas,
    validate_required,
    validate_rut,
)
from extract_info.models import EstadoExtraccion


class TestValidateRequired:
    def test_valid(self):
        errors = []
        validate_required("value", "Test", errors)
        assert errors == []

    def test_empty_string(self):
        errors = []
        validate_required("", "Test", errors)
        assert "Test" in errors

    def test_none(self):
        errors = []
        validate_required(None, "Test", errors)
        assert "Test" in errors

    def test_whitespace_only(self):
        errors = []
        validate_required("   ", "Test", errors)
        assert "Test" in errors


class TestValidateRut:
    def test_valid_rut(self):
        errors = []
        validate_rut("12.345.678-5", errors)
        assert errors == []

    def test_valid_rut_k(self):
        errors = []
        validate_rut("12.345.678-K", errors)
        assert errors == []

    def test_invalid_format(self):
        errors = []
        validate_rut("12345678-5", errors)
        assert len(errors) == 1

    def test_none(self):
        errors = []
        validate_rut(None, errors)
        assert "RUT" in errors


class TestValidateFecha:
    def test_valid(self):
        errors = []
        validate_fecha("25-06-2024", "Fecha", errors)
        assert errors == []

    def test_invalid_format(self):
        errors = []
        validate_fecha("2024-06-25", "Fecha", errors)
        assert len(errors) == 1

    def test_none(self):
        errors = []
        validate_fecha(None, "Fecha", errors)
        assert "Fecha" in errors


class TestValidateNumero:
    def test_valid(self):
        errors = []
        validate_numero("12345", "Proto", 1, 7, errors)
        assert errors == []

    def test_too_short(self):
        errors = []
        validate_numero("12", "Proto", 5, 7, errors)
        assert len(errors) == 1

    def test_none(self):
        errors = []
        validate_numero(None, "Proto", 1, 7, errors)
        assert "Proto" in errors


class TestValidatePaginas:
    def test_valid(self):
        errors = []
        validate_paginas(5, errors)
        assert errors == []

    def test_zero(self):
        errors = []
        validate_paginas(0, errors)
        assert len(errors) == 1

    def test_none(self):
        errors = []
        validate_paginas(None, errors)
        assert len(errors) == 1


class TestValidateCampos:
    def test_all_valid(self):
        campos = {
            "nombre_completo": "Juan Pérez",
            "rut": "12.345.678-5",
            "fecha_contrato": "25-06-2024",
            "proto": 12345,
            "repertorio": 6789,
            "fecha_repertorio": "20-06-2024",
            "cantidad_hojas": 5,
        }
        estado, obs = validate_campos(campos)
        assert estado == EstadoExtraccion.EXITO
        assert obs == ""

    def test_missing_nombre(self):
        campos = {
            "nombre_completo": None,
            "rut": "12.345.678-5",
            "fecha_contrato": "25-06-2024",
            "proto": 12345,
            "repertorio": 6789,
            "fecha_repertorio": "20-06-2024",
            "cantidad_hojas": 5,
        }
        estado, obs = validate_campos(campos)
        assert estado == EstadoExtraccion.ADVERTENCIA
        assert "Nombre completo" in obs

    def test_multiple_missing(self):
        campos = {
            "nombre_completo": None,
            "rut": None,
            "fecha_contrato": "25-06-2024",
            "proto": 12345,
            "repertorio": 6789,
            "fecha_repertorio": "20-06-2024",
            "cantidad_hojas": 5,
        }
        estado, obs = validate_campos(campos)
        assert estado == EstadoExtraccion.ADVERTENCIA
        assert "Nombre completo" in obs
        assert "RUT" in obs
