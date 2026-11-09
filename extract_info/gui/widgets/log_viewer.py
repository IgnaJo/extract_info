"""Visor de logs con estilo dark."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from extract_info.pipelines.base import LogEntry


class LogViewer(QPlainTextEdit):
    """Panel de logs con estilo dark y guardado automático a JSON."""

    LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("logViewer")

        # Fuente monoespaciada
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Asegurar directorio de logs
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def add_log(self, entry: LogEntry) -> None:
        """Añade una entrada de log al visor con color según nivel."""
        timestamp = entry.timestamp[:19].replace("T", " ")
        level = entry.level.upper()
        message = entry.message

        # Color según nivel
        if level == "ERROR":
            color = "#ff6b6b"
        elif level == "WARNING":
            color = "#ffd93d"
        else:
            color = "#a0e0a0"

        html = (
            f'<span style="color:#888;">[{timestamp}]</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:#ddd;">{message}</span>'
        )

        self.appendHtml(html)

        # Auto-scroll al final
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def add_logs(self, entries: list[LogEntry]) -> None:
        for entry in entries:
            self.add_log(entry)

    def clear(self) -> None:
        super().clear()