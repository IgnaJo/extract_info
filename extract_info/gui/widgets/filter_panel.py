"""Panel de filtros para la tabla de resultados."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

from extract_info.gui import theme


class FilterPanel(tk.Frame):
    """Panel de filtros para refinar la visualización de resultados."""

    def __init__(
        self,
        parent: tk.Widget,
        on_filter_change: Callable[[Dict[str, Any]], None],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.configure(bg=theme.BG)
        self.on_filter_change = on_filter_change

        self._setup_ui()

    def _setup_ui(self) -> None:
        tk.Label(
            self,
            text="Filtros:",
            font=theme.FONT_BODY_BOLD,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Estado
        tk.Label(
            self, text="Estado:",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT, padx=(0, 2))
        self.combo_estado = ttk.Combobox(
            self,
            values=["", "OK", "REVISAR", "ERROR", "EXITO", "ADVERTENCIA"],
            state="readonly",
            width=12,
        )
        self.combo_estado.set("")
        self.combo_estado.bind("<<ComboboxSelected>>", self._on_filter_change)
        self.combo_estado.bind("<<Clear>>", self._on_filter_change)
        self.combo_estado.pack(side=tk.LEFT, padx=(0, 10))

        # Carpeta
        tk.Label(
            self, text="Carpeta:",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT, padx=(0, 2))
        self.combo_carpeta = ttk.Combobox(
            self,
            values=[""],
            state="readonly",
            width=15,
        )
        self.combo_carpeta.set("")
        self.combo_carpeta.bind("<<ComboboxSelected>>", self._on_filter_change)
        self.combo_carpeta.pack(side=tk.LEFT, padx=(0, 10))

        # Proto
        tk.Label(
            self, text="Proto:",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT, padx=(0, 2))
        self.entry_proto = ttk.Entry(self, width=10)
        self.entry_proto.bind("<Return>", self._on_filter_change)
        self.entry_proto.bind("<FocusOut>", self._on_filter_change)
        self.entry_proto.pack(side=tk.LEFT, padx=(0, 10))

        # Repertorio
        tk.Label(
            self, text="Rep:",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT, padx=(0, 2))
        self.entry_rep = ttk.Entry(self, width=10)
        self.entry_rep.bind("<Return>", self._on_filter_change)
        self.entry_rep.bind("<FocusOut>", self._on_filter_change)
        self.entry_rep.pack(side=tk.LEFT, padx=(0, 10))

        # Limpiar
        self.btn_clear = ttk.Button(
            self,
            text="Limpiar",
            command=self._clear_filters,
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(10, 0))

    def update_folder_list(self, folders: List[str]) -> None:
        """Actualiza la lista de carpetas disponibles en el combobox."""
        self.combo_carpeta["values"] = [""] + folders
        self.combo_carpeta.set("")

    def get_filters(self) -> Dict[str, Any]:
        """Retorna los filtros actuales."""
        filters = {}
        estado = self.combo_estado.get()
        if estado:
            filters["estado"] = estado
        carpeta = self.combo_carpeta.get()
        if carpeta:
            filters["carpeta"] = carpeta
        proto = self.entry_proto.get().strip()
        if proto:
            filters["proto"] = proto
        rep = self.entry_rep.get().strip()
        if rep:
            filters["repertorio"] = rep
        return filters

    def _on_filter_change(self, event: Optional[tk.Event] = None) -> None:
        filters = self.get_filters()
        self.on_filter_change(filters)

    def _clear_filters(self) -> None:
        self.combo_estado.set("")
        self.combo_carpeta.set("")
        self.entry_proto.delete(0, tk.END)
        self.entry_rep.delete(0, tk.END)
        self.on_filter_change({})
