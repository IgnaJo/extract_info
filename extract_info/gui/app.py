"""Aplicación principal GUI para extracción de metadatos PDF."""

from __future__ import annotations

import csv
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from extract_info.gui import theme
from extract_info.gui.nodes.base import BaseNode, LogEntry, NodeResult
from extract_info.gui.nodes.registry import NodeRegistry
from extract_info.gui.widgets.drop_zone import DropZone
from extract_info.gui.widgets.filter_panel import FilterPanel
from extract_info.gui.widgets.log_viewer import LogViewer
from extract_info.gui.widgets.results_table import ResultsTable


class App:
    """Aplicación principal GUI."""

    def __init__(self):
        """Inicializa la aplicación."""
        self.root = tk.Tk()
        self.root.title("Extractor de Metadatos PDF")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=theme.BG)

        # Aplicar tema ttk
        theme.apply_style(self.root)

        # Estado de la aplicación
        self.current_node: Optional[BaseNode] = None
        self.current_result: Optional[NodeResult] = None
        self.is_processing = False
        self._cancel_flag = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Inicialmente NO pausado
        self._processing_thread: Optional[threading.Thread] = None
        self._thread_queue: queue.Queue = queue.Queue()

        # Descubrir nodos disponibles
        NodeRegistry.discover()

        self._setup_ui()
        self._setup_menu()
        self._update_action_buttons()
        self._poll_thread_queue()

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario."""
        main_frame = tk.Frame(self.root, padx=10, pady=10, bg=theme.BG)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._setup_header(main_frame)
        self._setup_drop_zone(main_frame)
        self._setup_action_bar(main_frame)
        self._setup_filters(main_frame)
        self._setup_results_table(main_frame)
        self._setup_bottom_panel(main_frame)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _setup_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=theme.BG)
        header.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header,
            text="Extractor de Metadatos PDF",
            font=theme.FONT_TITLE,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT)

        node_frame = tk.Frame(header, bg=theme.BG)
        node_frame.pack(side=tk.RIGHT)

        tk.Label(
            node_frame,
            text="Pipeline:",
            font=theme.FONT_BODY,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.combo_node = ttk.Combobox(
            node_frame,
            values=NodeRegistry.list_nodes(),
            state="readonly",
            width=20,
        )
        self.combo_node.bind("<<ComboboxSelected>>", self._on_node_change)
        self.combo_node.pack(side=tk.LEFT)

        nodes = NodeRegistry.list_nodes()
        if nodes:
            self.combo_node.set(nodes[0])
            self.current_node = NodeRegistry.get_node(nodes[0])

    # ------------------------------------------------------------------
    # Drop Zone
    # ------------------------------------------------------------------

    def _setup_drop_zone(self, parent: tk.Widget) -> None:
        self.drop_zone = DropZone(
            parent,
            on_drop_callback=self._on_folder_selected,
            on_clear_callback=self._on_selection_cleared,
            height=100,
        )
        self.drop_zone.pack(fill=tk.X, pady=(0, 8))

    def _on_folder_selected(self, path: str) -> None:
        """Se llama cuando el usuario selecciona una carpeta (drop o botón)."""
        self._update_action_buttons()

    def _on_selection_cleared(self) -> None:
        """Se llama cuando el usuario limpia la selección."""
        self._update_action_buttons()

    # ------------------------------------------------------------------
    # Action Bar (Ejecutar / Pausar / Cancelar)
    # ------------------------------------------------------------------

    def _setup_action_bar(self, parent: tk.Widget) -> None:
        bar = tk.Frame(parent, bg=theme.BG)
        bar.pack(fill=tk.X, pady=(0, 8))

        # Ejecutar
        self.btn_run = ttk.Button(
            bar,
            text="▶ Ejecutar",
            style="Primary.TButton",
            command=self._start_processing,
        )
        self.btn_run.pack(side=tk.LEFT, padx=(0, 8))

        # Pausar / Reanudar
        self.btn_pause = ttk.Button(
            bar,
            text="⏸ Pausar",
            style="Warning.TButton",
            command=self._on_pause_toggle,
        )
        self.btn_pause.pack(side=tk.LEFT, padx=(0, 8))

        # Cancelar
        self.btn_cancel = ttk.Button(
            bar,
            text="⏹ Cancelar",
            style="Danger.TButton",
            command=self._on_cancel,
        )
        self.btn_cancel.pack(side=tk.LEFT, padx=(0, 8))

        # Separador visual
        ttk.Separator(bar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10, pady=2,
        )

        # Exportar CSV
        self.btn_export = ttk.Button(
            bar,
            text="📥 Exportar CSV",
            command=self._export_csv,
        )
        self.btn_export.pack(side=tk.LEFT)

        # Estado (derecha)
        self.action_status = tk.Label(
            bar,
            text="Selecciona una carpeta para comenzar",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_SECONDARY,
            bg=theme.BG,
        )
        self.action_status.pack(side=tk.RIGHT)

    def _update_action_buttons(self) -> None:
        """Habilita/deshabilita botones según el estado actual."""
        has_path = self.drop_zone.get_selected_path() is not None

        if self.is_processing:
            self.btn_run.configure(state=tk.DISABLED)
            self.btn_pause.configure(state=tk.NORMAL)
            self.btn_cancel.configure(state=tk.NORMAL)
            self.btn_export.configure(state=tk.DISABLED)
            self.drop_zone.configure(state=tk.DISABLED)
        else:
            self.btn_run.configure(
                state=tk.NORMAL if has_path else tk.DISABLED,
            )
            self.btn_pause.configure(state=tk.DISABLED)
            self.btn_cancel.configure(state=tk.DISABLED)
            has_result = self.current_result is not None and len(self.current_result.rows) > 0
            self.btn_export.configure(
                state=tk.NORMAL if has_result else tk.DISABLED,
            )
            self.drop_zone.configure(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------

    def _setup_filters(self, parent: tk.Widget) -> None:
        self.filter_panel = FilterPanel(
            parent,
            on_filter_change=self._on_filter_change,
        )
        self.filter_panel.pack(fill=tk.X, pady=(0, 8))

    # ------------------------------------------------------------------
    # Tabla de resultados
    # ------------------------------------------------------------------

    def _setup_results_table(self, parent: tk.Widget) -> None:
        self.results_table = ResultsTable(parent)
        self.results_table.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        if self.current_node:
            self.results_table.set_columns(self.current_node.csv_columns)

    # ------------------------------------------------------------------
    # Panel inferior (logs + info)
    # ------------------------------------------------------------------

    def _setup_bottom_panel(self, parent: tk.Widget) -> None:
        bottom = tk.Frame(parent, bg=theme.BG)
        bottom.pack(fill=tk.X)

        self.log_viewer = LogViewer(bottom)
        self.log_viewer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        info_frame = tk.Frame(bottom, bg=theme.BG)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.progress_label = tk.Label(
            info_frame,
            text="Listo",
            font=theme.FONT_SMALL,
            fg=theme.TEXT_SECONDARY,
            bg=theme.BG,
            anchor="w",
        )
        self.progress_label.pack(fill=tk.X, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(
            info_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            length=200,
        )
        self.progress_bar.pack(fill=tk.X)

    # ------------------------------------------------------------------
    # Menú
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(
            label="Seleccionar carpeta...",
            command=self._select_folder,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Acerca de", command=self._show_about)

    # ------------------------------------------------------------------
    # Cambio de nodo
    # ------------------------------------------------------------------

    def _on_node_change(self, event: Optional[tk.Event] = None) -> None:
        node_name = self.combo_node.get()
        self.current_node = NodeRegistry.get_node(node_name)

        if self.current_node:
            self.results_table.set_columns(self.current_node.csv_columns)
            self.results_table.clear()
            self.current_result = None
            self._update_action_buttons()

            self.log_viewer.add_log(LogEntry(
                timestamp=datetime.now().isoformat(),
                level="INFO",
                message=f"Nodo seleccionado: {self.current_node.name}",
                node_name=self.current_node.name,
            ))

    # ------------------------------------------------------------------
    # Procesamiento
    # ------------------------------------------------------------------

    def _start_processing(self) -> None:
        """Inicia el procesamiento de la carpeta seleccionada."""
        path = self.drop_zone.get_selected_path()
        if not path:
            messagebox.showwarning(
                "Sin selección",
                "Selecciona una carpeta primero.",
            )
            return

        if self.current_node is None:
            messagebox.showerror(
                "Error",
                "Selecciona un pipeline primero.",
            )
            return

        self.is_processing = True
        self._cancel_flag = False
        self._pause_event.set()  # Asegurar que no está pausado
        self._update_action_buttons()
        self.action_status.configure(text="Procesando...")

        self._processing_thread = threading.Thread(
            target=self._process_folder,
            args=(path,),
            daemon=True,
        )
        self._processing_thread.start()

    def _process_folder(self, path: str) -> None:
        """Procesa una carpeta en hilo separado."""
        try:
            def progress_callback(current: int, total: int, filename: str):
                self._thread_queue.put(("progress", current, total, filename))

            def cancel_check() -> bool:
                return self._cancel_flag

            result = self.current_node.process_folder(
                path,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
                pause_event=self._pause_event,
            )

            self._thread_queue.put(("complete", result))

        except Exception as e:
            self._thread_queue.put(("error", str(e)))

    def _poll_thread_queue(self) -> None:
        """Pollea mensajes del hilo de procesamiento de forma segura en macOS."""
        try:
            while True:
                msg = self._thread_queue.get_nowait()
                if msg[0] == "progress":
                    self._update_progress(msg[1], msg[2], msg[3])
                elif msg[0] == "complete":
                    self._on_processing_complete(msg[1])
                elif msg[0] == "error":
                    self._on_processing_error(msg[1])
        except queue.Empty:
            pass
        self.root.after(50, self._poll_thread_queue)

    def _update_progress(self, current: int, total: int, filename: str) -> None:
        self.progress_bar["maximum"] = total
        self.progress_bar["value"] = current
        state = "⏸ Pausado" if not self._pause_event.is_set() else "Procesando"
        self.progress_label.configure(text=f"{state} {current}/{total}: {filename}")

    def _on_processing_complete(self, result: NodeResult) -> None:
        self.is_processing = False
        self.current_result = result
        self._pause_event.set()

        self.results_table.set_data(result.rows)

        folders = list(set(
            row.get("nombre_carpeta", row.get("Nombre Carpeta", ""))
            for row in result.rows
            if row.get("nombre_carpeta", row.get("Nombre Carpeta", ""))
        ))
        self.filter_panel.update_folder_list(folders)

        self.log_viewer.add_logs(result.logs)
        self.log_viewer.save_to_json()

        self._update_action_buttons()

        self.progress_bar["value"] = self.progress_bar["maximum"]
        self.progress_label.configure(
            text=f"Completado: {result.total_processed} archivos "
                 f"({result.success_count} OK, {result.warning_count} warnings, "
                 f"{result.error_count} errores)"
        )
        self.action_status.configure(text="Proceso completado")

    def _on_processing_error(self, error_msg: str) -> None:
        self.is_processing = False
        self._pause_event.set()
        self._update_action_buttons()
        self.progress_label.configure(text="Error en procesamiento")
        self.action_status.configure(text="Error")
        messagebox.showerror(
            "Error de procesamiento",
            f"Ocurrió un error:\n{error_msg}",
        )

    # ------------------------------------------------------------------
    # Pausa / Cancelación
    # ------------------------------------------------------------------

    def _on_pause_toggle(self) -> None:
        """Alterna entre pausar y reanudar."""
        if self._pause_event.is_set():
            # Pausar: bloquear el evento
            self._pause_event.clear()
            self.btn_pause.configure(text="▶ Reanudar")
            self.action_status.configure(text="⏸ Pausado")
        else:
            # Reanudar: liberar el evento
            self._pause_event.set()
            self.btn_pause.configure(text="⏸ Pausar")
            self.action_status.configure(text="Procesando...")

    def _on_cancel(self) -> None:
        """Cancela el procesamiento actual."""
        if messagebox.askyesno(
            "Cancelar procesamiento",
            "¿Estás seguro de que deseas cancelar?\n\n"
            "Se perderán los archivos no procesados.",
        ):
            self._cancel_flag = False  # Liberar pausa para que el loop pueda salir
            self._pause_event.set()
            self._cancel_flag = True
            self.action_status.configure(text="Cancelando...")

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------

    def _on_filter_change(self, filters: Dict[str, any]) -> None:
        self.results_table.apply_filters(filters)

    # ------------------------------------------------------------------
    # Exportar
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if self.current_result is None or not self.current_result.rows:
            messagebox.showwarning(
                "Sin datos",
                "No hay resultados para exportar.",
            )
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"resultado_{self.current_node.name}_{timestamp}.csv"

        filepath = filedialog.asksaveasfilename(
            title="Guardar CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile=default_name,
        )

        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.current_result.columns,
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(self.current_result.rows)

            messagebox.showinfo(
                "Exportación exitosa",
                f"CSV generado:\n{filepath}\n\n"
                f"Registros: {len(self.current_result.rows)}",
            )

            self.log_viewer.add_log(LogEntry(
                timestamp=datetime.now().isoformat(),
                level="INFO",
                message=f"CSV exportado: {filepath}",
                node_name=self.current_node.name,
            ))

        except Exception as e:
            messagebox.showerror(
                "Error de exportación",
                f"Error al guardar el CSV:\n{e}",
            )

    # ------------------------------------------------------------------
    # Menú acciones
    # ------------------------------------------------------------------

    def _select_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona la carpeta con PDFs")
        if folder:
            self.drop_zone._process_path(folder)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Acerca de",
            "Extractor de Metadatos PDF\n\n"
            "Versión: 1.0.0\n"
            "Pipeline actual: "
            f"{self.current_node.name if self.current_node else 'Ninguno'}\n\n"
            "Nodos disponibles:\n"
            + "\n".join(f"  - {name}" for name in NodeRegistry.list_nodes()),
        )

    def run(self) -> None:
        self.root.mainloop()
