"""Widget de tabla para mostrar resultados de extracción."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional

from extract_info.gui import theme


class ResultsTable(tk.Frame):
    """Tabla read-only para mostrar resultados de extracción.

    Se adapta dinámicamente al número y nombre de columnas
    según el nodo seleccionado.
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        """Inicializa la tabla de resultados.

        Args:
            parent: Widget padre de Tkinter.
            **kwargs: Argumentos adicionales para tk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.configure(bg=theme.BG)

        self.columns: List[str] = []
        self._col_ids: Dict[str, str] = {}
        self.data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura la interfaz de la tabla."""
        header_frame = tk.Frame(self, bg=theme.BG)
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.label_title = tk.Label(
            header_frame,
            text="Resultados",
            font=theme.FONT_BODY_BOLD,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
            anchor="w",
        )
        self.label_title.pack(side=tk.LEFT)

        self.label_count = tk.Label(
            header_frame,
            text="0 registros",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_SECONDARY,
            bg=theme.BG,
            anchor="e",
        )
        self.label_count.pack(side=tk.RIGHT)

        table_frame = tk.Frame(self, bg=theme.BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(table_frame, show="headings", selectmode="none")

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def set_columns(self, columns: List[str]) -> None:
        """Actualiza las columnas de la tabla.

        Args:
            columns: Lista de nombres de columnas.
        """
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = []

        self.columns = columns

        self._col_ids = {}
        col_ids = []
        for i, col in enumerate(columns):
            col_id = f"col{i}"
            self._col_ids[col_id] = col
            col_ids.append(col_id)

        self.tree["columns"] = col_ids

        for col_id, display_name in self._col_ids.items():
            self.tree.heading(col_id, text=display_name, anchor="w")
            width = max(100, len(display_name) * 10 + 20)
            self.tree.column(col_id, width=width, minwidth=80, anchor="w")

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Actualiza los datos de la tabla.

        Args:
            data: Lista de diccionarios con los datos.
        """
        self.data = data
        self.filtered_data = data.copy()
        self._refresh_table()

    def apply_filters(self, filters: Dict[str, Any]) -> None:
        """Aplica filtros a los datos mostrados.

        Args:
            filters: Diccionario con los filtros a aplicar.
        """
        self.filtered_data = self.data.copy()

        if filters.get("estado"):
            self.filtered_data = [
                row for row in self.filtered_data
                if self._get_field(row, "estado", "Estado").upper()
                == filters["estado"].upper()
            ]

        if filters.get("carpeta"):
            self.filtered_data = [
                row for row in self.filtered_data
                if self._get_field(row, "carpeta", "nombre_carpeta")
                == filters["carpeta"]
            ]

        if filters.get("proto"):
            proto_filter = str(filters["proto"])
            self.filtered_data = [
                row for row in self.filtered_data
                if proto_filter in str(self._get_field(row, "proto", "proto", "PROTOCOLIZADO Nº"))
            ]

        if filters.get("repertorio"):
            rep_filter = str(filters["repertorio"])
            self.filtered_data = [
                row for row in self.filtered_data
                if rep_filter in str(self._get_field(row, "rep", "repertorio", "REP Nº"))
            ]

        self._refresh_table()

    def _get_field(self, row: Dict[str, Any], *field_names: str) -> str:
        """Obtiene un campo del diccionario probando múltiples nombres.

        Args:
            row: Diccionario con los datos.
            *field_names: Nombres posibles del campo.

        Returns:
            Valor del campo o cadena vacía.
        """
        for name in field_names:
            if name in row and row[name] is not None:
                return str(row[name])
        return ""

    def _refresh_table(self) -> None:
        """Refresca la visualización de la tabla."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in self.filtered_data:
            values = [self._get_field(row, col) for col in self.columns]
            self.tree.insert("", tk.END, values=values)

        total = len(self.data)
        shown = len(self.filtered_data)
        if total == shown:
            self.label_count.configure(text=f"{total} registros")
        else:
            self.label_count.configure(text=f"{shown} de {total} registros")

    def get_selected_rows(self) -> List[Dict[str, Any]]:
        """Obtiene las filas seleccionadas (para uso futuro).

        Returns:
            Lista de diccionarios con las filas seleccionadas.
        """
        return []

    def clear(self) -> None:
        """Limpia la tabla completamente."""
        self.data = []
        self.filtered_data = []
        self._col_ids = {}
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = []
        self.label_count.configure(text="0 registros")
