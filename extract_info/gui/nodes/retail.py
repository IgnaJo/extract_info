"""Nodo Retail: wrapper del pipeline actual de contratos de tarjeta de crédito."""

from __future__ import annotations

import os
from typing import List, Optional

from extract_info.gui.nodes.base import BaseNode
from extract_info.models import ContratoSchema
from extract_info.pipeline import process_pdf


class RetailNode(BaseNode):
    """Nodo para extracción de contratos de tarjeta de crédito (Retail).

    Envuelve el pipeline existente y adapta su output al formato
    de nodo estándar.
    """

    @property
    def name(self) -> str:
        return "Retail"

    @property
    def description(self) -> str:
        return "Contratos de tarjeta de crédito - Retail"

    @property
    def csv_columns(self) -> List[str]:
        return [
            "nombre_archivo",
            "nombre_completo",
            "rut",
            "fecha_contrato",
            "proto",
            "repertorio",
            "fecha_repertorio",
            "cantidad_hojas",
            "nombre_carpeta",
            "estado_extraccion",
            "observaciones",
        ]

    def process_single(self, pdf_path: str) -> dict:
        """Procesa un solo PDF usando el pipeline de Retail.

        Args:
            pdf_path: Ruta completa al archivo PDF.

        Returns:
            Diccionario con los campos extraídos.
        """
        folder_name = os.path.basename(os.path.dirname(pdf_path))
        result: ContratoSchema = process_pdf(pdf_path, folder_name)

        return {
            "nombre_archivo": result.nombre_archivo,
            "nombre_completo": result.nombre_completo,
            "rut": result.rut,
            "fecha_contrato": result.fecha_contrato,
            "proto": result.proto,
            "repertorio": result.repertorio,
            "fecha_repertorio": result.fecha_repertorio,
            "cantidad_hojas": result.cantidad_hojas,
            "nombre_carpeta": result.nombre_carpeta,
            "estado_extraccion": result.estado_extraccion.value,
            "observaciones": result.observaciones,
        }

    def _create_error_row(self, filename: str, error_msg: str) -> dict:
        """Crea fila de error para el nodo Retail."""
        return {
            "nombre_archivo": filename,
            "nombre_completo": "ERROR",
            "rut": "0.000.000-0",
            "fecha_contrato": "00-00-0000",
            "proto": 1,
            "repertorio": 1,
            "fecha_repertorio": "00-00-0000",
            "cantidad_hojas": 0,
            "nombre_carpeta": "",
            "estado_extraccion": "ERROR",
            "observaciones": error_msg,
        }
