"""Nodo Aseguradora: adaptación del Extractor.py original a PyMuPDF."""

from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from extract_info.gui.nodes.base import BaseNode


class AseguradoraNode(BaseNode):
    """Nodo para extracción de documentos de aseguradora.

    Adaptado del Extractor.py original, mantiene la funcionalidad
    de extracción por coordenadas hardcoded y búsqueda en penúltima página.
    """

    # Coordenadas hardcoded (mantenidas fijas del Extractor.py original)
    ZONA_PROTO = (445, 18, 520, 45)
    ZONA_REP_NUM = (405, 35, 455, 60)
    ZONA_REP_FECHA = (465, 35, 555, 60)

    # Patrones regex (mantenidos del original)
    PAT_RUN = re.compile(
        r"RUN\s+del\s+Firmante\s*:\s*(\d{1,2}\.\d{3}\.\d{3}-[0-9Kk])",
        re.IGNORECASE,
    )
    PAT_NOMBRE = re.compile(r"Nombre\s*:\s*(.+)", re.IGNORECASE)
    PAT_FECHA_FIRMA = re.compile(
        r"Fecha\s+de\s+la\s+Firma\s*:\s*(\d{2}[-/]\d{2}[-/]\d{4})",
        re.IGNORECASE,
    )
    PAT_FECHA = re.compile(r"\d{2}-\d{2}-\d{4}")

    @property
    def name(self) -> str:
        return "Aseguradora"

    @property
    def description(self) -> str:
        return "Documentos de Aseguradora - Notarial"

    @property
    def csv_columns(self) -> List[str]:
        return [
            "Archivo",
            "Fecha Firma",
            "RUN Firmante",
            "Nombre Firmante",
            "REP Nº",
            "PROTOCOLIZADO Nº",
            "REP Fecha",
            "Cantidad de páginas",
            "Estado",
        ]

    def process_single(self, pdf_path: str) -> dict:
        """Procesa un solo PDF usando el método de Aseguradora.

        Extrae:
        - Protocolo, REP N°, REP Fecha de primera página (por coordenadas)
        - RUN, Nombre, Fecha Firma de penúltima página

        Args:
            pdf_path: Ruta completa al archivo PDF.

        Returns:
            Diccionario con los campos extraídos en formato Aseguradora.
        """
        filename = os.path.splitext(os.path.basename(pdf_path))[0]

        doc = fitz.open(pdf_path)
        try:
            page_0 = doc[0]

            # Extraer de primera página por coordenadas
            protocol = self._extract_digits_from_zone(page_0, self.ZONA_PROTO)
            rep_num = self._extract_digits_from_zone(page_0, self.ZONA_REP_NUM)
            rep_fecha = self._extract_date_from_zone(page_0, self.ZONA_REP_FECHA)

            # Extraer de penúltima página
            run, nombre, fecha_firma = None, None, None
            if len(doc) >= 2:
                penultimate = doc[-2]
                text = penultimate.get_text()

                m_run = self.PAT_RUN.search(text)
                m_nombre = self.PAT_NOMBRE.search(text)
                m_fecha = self.PAT_FECHA_FIRMA.search(text)

                if m_run:
                    run = m_run.group(1).strip()
                if m_nombre:
                    nombre = m_nombre.group(1).strip()
                if m_fecha:
                    fecha_firma = m_fecha.group(1).replace("/", "-")

            page_count = len(doc)

        finally:
            doc.close()

        # Validar consistencia
        estado = self._verificar_consistencia(
            fecha_firma, run, nombre, protocol, rep_num, rep_fecha, page_count
        )

        return {
            "Archivo": filename,
            "Fecha Firma": fecha_firma,
            "RUN Firmante": run,
            "Nombre Firmante": nombre,
            "REP Nº": rep_num,
            "PROTOCOLIZADO Nº": protocol,
            "REP Fecha": rep_fecha,
            "Cantidad de páginas": page_count,
            "Estado": estado,
        }

    def _extract_digits_from_zone(
        self, page: fitz.Page, zone: Tuple[int, int, int, int]
    ) -> Optional[str]:
        """Extrae dígitos de una zona específica de la página.

        Args:
            page: Página de PyMuPDF.
            zone: Tupla (x0, y0, x1, y1) con las coordenadas.

        Returns:
            String con solo dígitos, o None si no hay dígitos.
        """
        rect = fitz.Rect(zone)
        text = page.get_text("text", clip=rect)
        digits = re.sub(r"\D", "", text)
        return digits if digits else None

    def _extract_date_from_zone(
        self, page: fitz.Page, zone: Tuple[int, int, int, int]
    ) -> Optional[str]:
        """Extrae fecha de una zona específica de la página.

        Args:
            page: Página de PyMuPDF.
            zone: Tupla (x0, y0, x1, y1) con las coordenadas.

        Returns:
            Fecha en formato dd-mm-yyyy, o None si no se encuentra.
        """
        rect = fitz.Rect(zone)
        text = page.get_text("text", clip=rect)
        m = self.PAT_FECHA.search(text)
        return m.group(0) if m else None

    def _verificar_consistencia(
        self,
        fecha_firma: Optional[str],
        run: Optional[str],
        nombre: Optional[str],
        protocol: Optional[str],
        rep_numero: Optional[str],
        rep_fecha: Optional[str],
        cantidad_paginas: int,
    ) -> str:
        """Verifica consistencia de los campos extraídos.

        Mantenida del Extractor.py original.

        Returns:
            "OK" si todos los campos son válidos, o "REVISAR: ..." con los errores.
        """
        errores = []

        if not fecha_firma:
            errores.append("Fecha Firma")
        if not run:
            errores.append("RUN")
        if not nombre:
            errores.append("Nombre")
        if not protocol or not re.fullmatch(r"\d{5,7}", protocol):
            errores.append("PROTOCOLIZADO")
        if not rep_numero or not re.fullmatch(r"\d{4,7}", rep_numero):
            errores.append("REP Nº")
        if not rep_fecha or not re.fullmatch(r"\d{2}-\d{2}-\d{4}", rep_fecha):
            errores.append("REP Fecha")
        if not cantidad_paginas or cantidad_paginas < 2:
            errores.append("Páginas")

        if errores:
            return "REVISAR: " + ", ".join(errores)

        return "OK"

    def _create_error_row(self, filename: str, error_msg: str) -> dict:
        """Crea fila de error para el nodo Aseguradora."""
        return {
            "Archivo": filename,
            "Fecha Firma": None,
            "RUN Firmante": None,
            "Nombre Firmante": None,
            "REP Nº": None,
            "PROTOCOLIZADO Nº": None,
            "REP Fecha": None,
            "Cantidad de páginas": 0,
            "Estado": f"ERROR: {error_msg}",
        }
