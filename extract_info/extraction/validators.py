"""Validación de campos extraídos y generación de estado."""

from __future__ import annotations

import re

from extract_info.models import EstadoExtraccion


def validate_required(value: str | None, field_name: str, errors: list[str]) -> None:
    """Valida que un campo obligatorio no esté vacío."""
    if not value or not value.strip():
        errors.append(field_name)


def validate_rut(rut: str | None, errors: list[str]) -> None:
    """Valida formato de RUT chileno."""
    if not rut:
        errors.append("RUT")
        return
    if not re.fullmatch(r"\d{1,2}\.\d{3}\.\d{3}-[\dkK]", rut):
        errors.append("RUT (formato inválido)")


def validate_fecha(fecha: str | None, field_name: str, errors: list[str]) -> None:
    """Valida formato de fecha dd-mm-yyyy."""
    if not fecha:
        errors.append(field_name)
        return
    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", fecha):
        errors.append(f"{field_name} (formato inválido)")


def validate_numero(value: str | None, field_name: str, min_digits: int, max_digits: int, errors: list[str]) -> None:
    """Valida que un valor numérico tenga la cantidad de dígitos correcta."""
    if not value:
        errors.append(field_name)
        return
    digits = re.sub(r"\D", "", value)
    if not digits or not (min_digits <= len(digits) <= max_digits):
        errors.append(f"{field_name} ({min_digits}-{max_digits} dígitos requeridos)")


def validate_paginas(cantidad: int | None, errors: list[str]) -> None:
    """Valida que haya al menos 1 página."""
    if not cantidad or cantidad < 1:
        errors.append("Cantidad de hojas")


def validate_campos(campos: dict[str, str | int | None]) -> tuple[EstadoExtraccion, str]:
    """Valida todos los campos extraídos y retorna estado + observaciones.

    Args:
        campos: Diccionario con los campos extraídos.

    Returns:
        Tupla de (estado_extraccion, observaciones).
    """
    errors: list[str] = []

    validate_required(campos.get("nombre_completo"), "Nombre completo", errors)
    validate_rut(campos.get("rut"), errors)
    validate_fecha(campos.get("fecha_contrato"), "Fecha contrato", errors)
    validate_numero(str(campos.get("proto")), "Protocolo", 1, 7, errors)
    validate_numero(str(campos.get("repertorio")), "Repertorio", 1, 7, errors)
    validate_fecha(campos.get("fecha_repertorio"), "Fecha repertorio", errors)
    validate_paginas(campos.get("cantidad_hojas"), errors)

    if errors:
        return EstadoExtraccion.ADVERTENCIA, "Campos faltantes o inválidos: " + ", ".join(errors)

    return EstadoExtraccion.EXITO, ""
