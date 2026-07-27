"""Tests para el esquema ContratoSchema."""

import pytest

from extract_info.models import ContratoSchema, EstadoExtraccion


def _make_valid(**overrides):
    base = dict(
        nombre_completo="Juan Pérez González",
        rut="12.345.678-5",
        fecha_contrato="25-06-2024",
        proto=12345,
        repertorio=6789,
        fecha_repertorio="20-06-2024",
        nombre_archivo="contrato_001.pdf",
        cantidad_hojas=5,
        nombre_carpeta="carpeta_1",
    )
    base.update(overrides)
    return base


class TestContratoSchema:
    def test_valid_schema(self):
        schema = ContratoSchema(**_make_valid())
        assert schema.estado_extraccion == EstadoExtraccion.EXITO
        assert schema.observaciones == ""

    def test_rut_invalid_pattern(self):
        with pytest.raises(Exception):
            ContratoSchema(**_make_valid(rut="12345678-5"))

    def test_rut_k_validator(self):
        schema = ContratoSchema(**_make_valid(rut="12.345.678-K"))
        assert schema.rut == "12.345.678-K"

    def test_fecha_contrato_invalid(self):
        with pytest.raises(Exception):
            ContratoSchema(**_make_valid(fecha_contrato="2024-06-25"))

    def test_proto_zero_invalid(self):
        with pytest.raises(Exception):
            ContratoSchema(**_make_valid(proto=0))

    def test_cantidad_hojas_minimum(self):
        schema = ContratoSchema(**_make_valid(cantidad_hojas=1))
        assert schema.cantidad_hojas == 1

    def test_estado_advertencia(self):
        schema = ContratoSchema(**_make_valid(estado_extraccion=EstadoExtraccion.ADVERTENCIA))
        assert schema.estado_extraccion == EstadoExtraccion.ADVERTENCIA

    def test_observaciones_default(self):
        schema = ContratoSchema(**_make_valid())
        assert schema.observaciones == ""

    def test_nombre_completo_empty_invalid(self):
        with pytest.raises(Exception):
            ContratoSchema(**_make_valid(nombre_completo=""))
