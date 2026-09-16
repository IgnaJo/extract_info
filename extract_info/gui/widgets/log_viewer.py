"""Widget para visualizar logs de procesamiento."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext
from typing import List, Optional

from extract_info.gui import theme
from extract_info.gui.nodes.base import LogEntry


class LogViewer(tk.Frame):
    """Panel de visualización de logs con guardado automático JSON."""

    LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=theme.BG)

        self.logs: List[LogEntry] = []
        self.max_entries = 100

        self._ensure_logs_dir()
        self._setup_ui()

    def _ensure_logs_dir(self) -> None:
        os.makedirs(self.LOGS_DIR, exist_ok=True)

    def _setup_ui(self) -> None:
        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill=tk.X, padx=5, pady=(5, 0))

        tk.Label(
            header,
            text="Logs",
            font=theme.FONT_BODY_BOLD,
            fg=theme.TEXT_PRIMARY,
            bg=theme.BG,
            anchor="w",
        ).pack(side=tk.LEFT)

        btn_open_folder = tk.Button(
            header,
            text="📂 Abrir Carpeta",
            command=self._open_logs_folder,
            font=theme.FONT_SMALL,
            bg=theme.SURFACE,
            fg=theme.PRIMARY,
            activebackground=theme.BORDER,
            activeforeground=theme.PRIMARY,
            relief="flat",
            cursor="hand2",
        )
        btn_open_folder.pack(side=tk.RIGHT)

        self.text_area = scrolledtext.ScrolledText(
            self,
            width=60,
            height=12,
            font=theme.FONT_MONO,
            state=tk.DISABLED,
            bg=theme.LOG_BG,
            fg=theme.LOG_FG,
            insertbackground=theme.LOG_FG,
            selectbackground=theme.PRIMARY,
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=1,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_area.tag_configure("INFO", foreground="#4ec9b0")
        self.text_area.tag_configure("WARNING", foreground="#dcdcaa")
        self.text_area.tag_configure("ERROR", foreground="#f44747")
        self.text_area.tag_configure("TIMESTAMP", foreground="#808080")

    def add_log(self, entry: LogEntry) -> None:
        """Agrega una entrada de log al visor."""
        self.logs.append(entry)
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
        self._refresh_display()

    def add_logs(self, entries: List[LogEntry]) -> None:
        """Agrega múltiples entradas de log."""
        self.logs.extend(entries)
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
        self._refresh_display()

    def _refresh_display(self) -> None:
        self.text_area.configure(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)

        for entry in self.logs:
            ts = entry.timestamp[:19] if entry.timestamp else ""
            self.text_area.insert(tk.END, f"{ts} ", "TIMESTAMP")
            self.text_area.insert(tk.END, f"{entry.message}\n", entry.level)

        self.text_area.see(tk.END)
        self.text_area.configure(state=tk.DISABLED)

    def save_to_json(self) -> str:
        """Guarda los logs actuales en un archivo JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"extraction_{timestamp}.json"
        filepath = os.path.join(self.LOGS_DIR, filename)

        data = {
            "timestamp": datetime.now().isoformat(),
            "total_entries": len(self.logs),
            "logs": [
                {
                    "timestamp": entry.timestamp,
                    "level": entry.level,
                    "message": entry.message,
                    "filename": entry.filename,
                    "node_name": entry.node_name,
                    "details": entry.details,
                }
                for entry in self.logs
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    def _open_logs_folder(self) -> None:
        logs_path = os.path.abspath(self.LOGS_DIR)
        if sys.platform == "darwin":
            subprocess.run(["open", logs_path], check=False)
        elif sys.platform == "win32":
            os.startfile(logs_path)
        else:
            subprocess.run(["xdg-open", logs_path], check=False)

    def clear(self) -> None:
        self.logs.clear()
        self.text_area.configure(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        self.text_area.configure(state=tk.DISABLED)
