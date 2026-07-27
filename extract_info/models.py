"""Esquemas Pydantic para validación de datos extraídos."""

from enum import Enum

from pydantic import BaseModel, Field


class EstadoExtraccion(str, Enum):
    EXITO = "EXITO"
    ADVERTENCIA = "ADVERTENCIA"
    ERROR = "ERROR"


class ContratoSchema(BaseModel):
    """Schema de salida para un documento procesado."""

    nombre_completo: str = Field(..., min_length=1, description="Nombre completo extraído")
    rut: str = Field(
        ...,
        pattern=r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$",
        description="RUT chileno validado",
    )
    fecha_contrato: str = Field(
        ...,
        pattern=r"^\d{2}-\d{2}-\d{4}$",
        description="Fecha normalizada dd-mm-yyyy",
    )
    proto: int = Field(..., ge=1, description="Número de protocolizado")
    repertorio: int = Field(..., ge=1, description="Número de repertorio")
    fecha_repertorio: str = Field(
        ...,
        pattern=r"^\d{2}-\d{2}-\d{4}$",
        description="Fecha de asignación del repertorio",
    )
    nombre_archivo: str = Field(..., min_length=1, description="Nombre del archivo PDF")
    cantidad_hojas: int = Field(..., ge=1, description="Total de páginas del PDF")
    nombre_carpeta: str = Field(..., min_length=1, description="Carpeta contenedora")
    estado_extraccion: EstadoExtraccion = Field(
        default=EstadoExtraccion.EXITO, description="Estado de la extracción"
    )
    observaciones: str = Field(default="", description="Detalle de campos faltantes o errores")
