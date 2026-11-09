"""Punto de entrada de la GUI PySide6."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from extract_info.gui.app import MainWindow


def get_qss_path() -> Path:
    """Retorna la ruta al archivo QSS, compatible con PyInstaller."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: sys._MEIPASS es la carpeta temporal de extracción
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "assets" / "styles" / "style.QSS"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Extractor de Metadatos PDF")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ExtractInfo")
    app.setOrganizationDomain("extractinfo.local")

    # High DPI support
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Cargar QSS global
    qss_path = get_qss_path()
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        raise FileNotFoundError(f"No se encontró el archivo QSS: {qss_path}")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
