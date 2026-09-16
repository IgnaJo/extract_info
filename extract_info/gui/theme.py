"""Tema visual centralizado para la GUI.

Define paleta de colores (WCAG AA compliant), fuentes y estilos ttk
para apariencia consistente en macOS, Windows y Linux.
"""

from __future__ import annotations

import platform
import tkinter as tk
from tkinter import ttk


# ---------------------------------------------------------------------------
# Paleta de colores (contraste mínimo 4.5:1 sobre BG)
# ---------------------------------------------------------------------------
BG = "#ffffff"
SURFACE = "#f5f5f5"
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#555555"
TEXT_DISABLED = "#999999"

PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
PRIMARY_ACTIVE = "#1e40af"

SUCCESS = "#16a34a"
SUCCESS_LIGHT = "#dcfce7"
WARNING = "#d97706"
WARNING_LIGHT = "#fef3c7"
ERROR = "#dc2626"
ERROR_LIGHT = "#fee2e2"

BORDER = "#d1d5db"
BORDER_FOCUS = "#93c5fd"

DROP_ZONE_BG = "#e8f0fe"
DROP_ZONE_HOVER = "#d2e3fc"
DROP_ZONE_BORDER = "#93c5fd"

LOG_BG = "#1e1e1e"
LOG_FG = "#d4d4d4"

TREE_ALT_ROW = "#f8fafc"
TREE_HEADER_BG = "#f1f5f9"
TREE_HEADER_FG = "#334155"

# ---------------------------------------------------------------------------
# Fuentes (cross-OS safe)
# ---------------------------------------------------------------------------
_system = platform.system()
if _system == "Darwin":
    _FONT_FAMILY = "Helvetica"
elif _system == "Windows":
    _FONT_FAMILY = "Segoe UI"
else:
    _FONT_FAMILY = "Helvetica"

FONT_TITLE = (_FONT_FAMILY, 16, "bold")
FONT_SUBTITLE = (_FONT_FAMILY, 12, "bold")
FONT_BODY = (_FONT_FAMILY, 10)
FONT_BODY_BOLD = (_FONT_FAMILY, 10, "bold")
FONT_SMALL = (_FONT_FAMILY, 9)
FONT_SMALL_BOLD = (_FONT_FAMILY, 9, "bold")
FONT_MONO = ("Courier", 9)

# ---------------------------------------------------------------------------
# ttk.Style
# ---------------------------------------------------------------------------

def apply_style(root: tk.Tk) -> ttk.Style:
    """Configura el tema ttk global para la aplicación.

    Usa el tema 'clam' como base (consistente cross-OS) y aplica
    la paleta de colores definida.

    Args:
        root: Ventana raíz de Tkinter.

    Returns:
        El objeto ttk.Style configurado.
    """
    style = ttk.Style(root)

    # Tema base: clam es el más consistente cross-OS
    available = style.theme_names()
    if "clam" in available:
        style.theme_use("clam")
    elif "alt" in available:
        style.theme_use("alt")

    # --- TTK Button ---
    style.configure(
        "TButton",
        font=FONT_BODY_BOLD,
        foreground=TEXT_PRIMARY,
        background=SURFACE,
        bordercolor=BORDER,
        lightcolor=SURFACE,
        darkcolor=SURFACE,
        relief="flat",
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[("active", BORDER), ("disabled", SURFACE)],
        foreground=[("disabled", TEXT_DISABLED)],
    )

    # Primary button (Ejecutar, Exportar)
    style.configure(
        "Primary.TButton",
        font=FONT_BODY_BOLD,
        foreground="#ffffff",
        background=PRIMARY,
        bordercolor=PRIMARY,
        lightcolor=PRIMARY,
        darkcolor=PRIMARY_ACTIVE,
        padding=(16, 8),
    )
    style.map(
        "Primary.TButton",
        background=[("active", PRIMARY_HOVER), ("disabled", TEXT_DISABLED)],
        foreground=[("disabled", "#cccccc")],
    )

    # Danger button (Cancelar)
    style.configure(
        "Danger.TButton",
        font=FONT_BODY_BOLD,
        foreground="#ffffff",
        background=ERROR,
        bordercolor=ERROR,
        lightcolor=ERROR,
        darkcolor="#b91c1c",
        padding=(12, 8),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#b91c1c"), ("disabled", TEXT_DISABLED)],
        foreground=[("disabled", "#cccccc")],
    )

    # Warning button (Pausar)
    style.configure(
        "Warning.TButton",
        font=FONT_BODY_BOLD,
        foreground="#ffffff",
        background=WARNING,
        bordercolor=WARNING,
        lightcolor=WARNING,
        darkcolor="#b45309",
        padding=(12, 8),
    )
    style.map(
        "Warning.TButton",
        background=[("active", "#b45309"), ("disabled", TEXT_DISABLED)],
        foreground=[("disabled", "#cccccc")],
    )

    # --- TTK Combobox ---
    style.configure(
        "TCombobox",
        font=FONT_BODY,
        foreground=TEXT_PRIMARY,
        fieldbackground=BG,
        background=SURFACE,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=4,
    )
    style.map(
        "TCombobox",
        bordercolor=[("focus", BORDER_FOCUS)],
        foreground=[("readonly", TEXT_PRIMARY)],
    )

    # --- TTK Entry ---
    style.configure(
        "TEntry",
        font=FONT_BODY,
        foreground=TEXT_PRIMARY,
        fieldbackground=BG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=4,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", BORDER_FOCUS)],
    )

    # --- TTK Treeview ---
    style.configure(
        "Treeview",
        font=FONT_BODY,
        foreground=TEXT_PRIMARY,
        background=BG,
        fieldbackground=BG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        rowheight=28,
        padding=4,
    )
    style.configure(
        "Treeview.Heading",
        font=FONT_BODY_BOLD,
        foreground=TREE_HEADER_FG,
        background=TREE_HEADER_BG,
        bordercolor=BORDER,
        lightcolor=TREE_HEADER_BG,
        darkcolor=TREE_HEADER_BG,
        relief="flat",
        padding=(8, 4),
    )
    style.map(
        "Treeview",
        background=[("selected", PRIMARY)],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", BORDER)],
    )

    # --- TTK Scrollbar ---
    style.configure(
        "TScrollbar",
        background=SURFACE,
        bordercolor=BORDER,
        arrowcolor=TEXT_SECONDARY,
        troughcolor=SURFACE,
        relief="flat",
    )
    style.map(
        "TScrollbar",
        background=[("active", BORDER)],
    )

    # --- TTK Progressbar ---
    style.configure(
        "TProgressbar",
        background=PRIMARY,
        troughcolor=SURFACE,
        bordercolor=BORDER,
        lightcolor=PRIMARY,
        darkcolor=PRIMARY_ACTIVE,
    )

    # --- TTK Label ---
    style.configure(
        "TLabel",
        font=FONT_BODY,
        foreground=TEXT_PRIMARY,
        background=BG,
    )

    # --- TTK Frame ---
    style.configure(
        "TFrame",
        background=BG,
    )

    # --- TTK Separator ---
    style.configure(
        "TSeparator",
        background=BORDER,
    )

    return style
