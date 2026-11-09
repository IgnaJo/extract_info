"""Esquemas Pydantic para validación de datos extraídos."""

from enum import Enum

from pydantic import BaseModel, Field


class EstadoExtraccion(str, Enum):
    EXITO = "EXITO"
    ADVERTENCIA = "ADVERTENCIA"
    ERROR = "ERROR"


class ContratoSchema(BaseModel):
    """Schema de salida para un documento procesado."""

    nombre_completo: str | None = Field(
        None, min_length=1, description="Nombre completo extraído (None si no se encontró)"
    )
    rut: str | None = Field(
        None,
        pattern=r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$",
        description="RUT chileno validado (None si no se encontró)",
    )
    fecha_contrato: str | None = Field(
        None,
        pattern=r"^\d{2}-\d{2}-\d{4}$",
        description="Fecha normalizada dd-mm-yyyy (None si no se encontró)",
    )
    proto: int | None = Field(
        None, ge=1, description="Número de protocolizado (None si no se encontró)"
    )
    repertorio: int | None = Field(
        None, ge=1, description="Número de repertorio (None si no se encontró)"
    )
    fecha_repertorio: str | None = Field(
        None,
        pattern=r"^\d{2}-\d{2}-\d{4}$",
        description="Fecha de asignación del repertorio (None si no se encontró)",
    )
    nombre_archivo: str = Field(..., min_length=1, description="Nombre del archivo PDF")
    cantidad_hojas: int | None = Field(
        None, ge=1, description="Total de páginas del PDF (None si no se pudo leer)"
    )
    nombre_carpeta: str = Field(..., min_length=1, description="Carpeta contenedora")
    estado_extraccion: EstadoExtraccion = Field(
        default=EstadoExtraccion.EXITO, description="Estado de la extracción"
    )
    observaciones: str = Field(default="", description="Detalle de campos faltantes o errores")
