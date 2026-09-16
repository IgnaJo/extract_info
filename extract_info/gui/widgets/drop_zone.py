"""Widget de arrastrar y soltar para carpetas de PDFs."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, Optional

from extract_info.gui import theme

try:
    import tkinterdnd2
    HAS_DND = True
except ImportError:
    HAS_DND = False


class DropZone(tk.Frame):
    """Widget de arrastrar y soltar carpetas.

    Muestra una zona visual donde el usuario puede arrastrar carpetas
    o seleccionar una con un botón. La ruta se guarda internamente
    y NO se procesa automáticamente — el usuario debe hacer clic
    en "Ejecutar" para iniciar el procesamiento.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_drop_callback: Callable[[str], None],
        on_clear_callback: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """Inicializa el DropZone.

        Args:
            parent: Widget padre de Tkinter.
            on_drop_callback: Función a llamar cuando se confirma una selección.
                Signature: (path: str) -> None
            on_clear_callback: Función opcional al limpiar la selección.
            **kwargs: Argumentos adicionales para tk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.on_drop = on_drop_callback
        self.on_clear = on_clear_callback
        self.selected_path: Optional[str] = None

        self.configure(
            bg=theme.DROP_ZONE_BG,
            relief="groove",
            bd=2,
            highlightbackground=theme.DROP_ZONE_BORDER,
            highlightthickness=1,
        )

        self._setup_ui()
        self._setup_dnd()

    def _setup_ui(self) -> None:
        """Configura la interfaz visual del drop zone."""
        # Fila principal: icono + textos + botones
        content = tk.Frame(self, bg=theme.DROP_ZONE_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Icono
        self.label_icon = tk.Label(
            content,
            text="📁",
            font=("Arial", 28),
            bg=theme.DROP_ZONE_BG,
        )
        self.label_icon.pack(side=tk.LEFT, padx=(0, 12))

        # Textos (centro)
        texts_frame = tk.Frame(content, bg=theme.DROP_ZONE_BG)
        texts_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.label_text = tk.Label(
            texts_frame,
            text="Arrastra una carpeta aquí",
            font=theme.FONT_SUBTITLE,
            bg=theme.DROP_ZONE_BG,
            fg=theme.TEXT_PRIMARY,
            anchor="w",
        )
        self.label_text.pack(fill=tk.X)

        self.label_subtext = tk.Label(
            texts_frame,
            text="También puedes arrastrar un archivo PDF individual",
            font=theme.FONT_SMALL,
            bg=theme.DROP_ZONE_BG,
            fg=theme.TEXT_SECONDARY,
            anchor="w",
        )
        self.label_subtext.pack(fill=tk.X)

        self.label_selected = tk.Label(
            texts_frame,
            text="",
            font=theme.FONT_SMALL_BOLD,
            bg=theme.DROP_ZONE_BG,
            fg=theme.PRIMARY,
            anchor="w",
        )
        self.label_selected.pack(fill=tk.X)

        # Botones (derecha)
        buttons_frame = tk.Frame(content, bg=theme.DROP_ZONE_BG)
        buttons_frame.pack(side=tk.RIGHT, padx=(10, 0))

        self.btn_select = tk.Button(
            buttons_frame,
            text="📂 Seleccionar",
            command=self._select_folder,
            font=theme.FONT_BODY_BOLD,
            bg=theme.PRIMARY,
            fg="#ffffff",
            activebackground=theme.PRIMARY_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.btn_select.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = tk.Button(
            buttons_frame,
            text="✕ Limpiar",
            command=self.clear_selection,
            font=theme.FONT_SMALL,
            bg=theme.SURFACE,
            fg=theme.TEXT_SECONDARY,
            activebackground=theme.BORDER,
            activeforeground=theme.TEXT_PRIMARY,
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
        )
        self.btn_clear.pack(side=tk.LEFT)

    def _setup_dnd(self) -> None:
        """Configura drag & drop si tkinterdnd2 está disponible."""
        if not HAS_DND:
            self.label_subtext.configure(
                text="Drag & drop no disponible — usa el botón Seleccionar"
            )
            return

        try:
            self.drop_target_register(tkinterdnd2.DND_FILES)
            self.dnd_bind("<<Drop>>", self._handle_drop)
            self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        except Exception:
            self.label_subtext.configure(
                text="Drag & drop no disponible — usa el botón Seleccionar"
            )

    # ------------------------------------------------------------------
    # Drag & drop events
    # ------------------------------------------------------------------

    def _on_drag_enter(self, event: tk.Event) -> None:
        self.configure(bg=theme.DROP_ZONE_HOVER)
        for w in (self.label_icon, self.label_text, self.label_subtext, self.label_selected):
            w.configure(bg=theme.DROP_ZONE_HOVER)

    def _on_drag_leave(self, event: tk.Event) -> None:
        self._reset_bg()

    def _handle_drop(self, event: tk.Event) -> None:
        self._reset_bg()
        path = event.data.strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        self._process_path(path)

    def _reset_bg(self) -> None:
        self.configure(bg=theme.DROP_ZONE_BG)
        for w in (self.label_icon, self.label_text, self.label_subtext, self.label_selected):
            w.configure(bg=theme.DROP_ZONE_BG)

    # ------------------------------------------------------------------
    # Selección manual
    # ------------------------------------------------------------------

    def _select_folder(self) -> None:
        """Abre diálogo para seleccionar carpeta."""
        folder = filedialog.askdirectory(title="Selecciona la carpeta con PDFs")
        if folder:
            self._process_path(folder)

    # ------------------------------------------------------------------
    # Procesamiento de ruta recibida
    # ------------------------------------------------------------------

    def _process_path(self, path: str) -> None:
        """Valida y guarda la ruta (NO procesa — solo almacena).

        Args:
            path: Ruta a procesar.
        """
        if not os.path.exists(path):
            messagebox.showerror("Error", f"La ruta no existe:\n{path}")
            return

        if os.path.isfile(path):
            if path.lower().endswith(".pdf"):
                self._set_selection(path, is_file=True)
            else:
                messagebox.showerror(
                    "Formato no válido",
                    f"El archivo no es un PDF:\n{os.path.basename(path)}",
                )
            return

        if os.path.isdir(path):
            pdf_count = len(
                [f for f in os.listdir(path) if f.lower().endswith(".pdf")]
            )
            if pdf_count == 0:
                messagebox.showwarning(
                    "Sin PDFs",
                    "La carpeta seleccionada no contiene archivos PDF.",
                )
                return
            self._set_selection(path, is_file=False, pdf_count=pdf_count)
            return

        messagebox.showerror(
            "Tipo no válido",
            f"La ruta no es un archivo ni una carpeta:\n{path}",
        )

    def _set_selection(
        self,
        path: str,
        is_file: bool = False,
        pdf_count: int = 0,
    ) -> None:
        """Actualiza la UI para reflejar la selección.

        Args:
            path: Ruta seleccionada.
            is_file: True si es un archivo individual.
            pdf_count: Cantidad de PDFs (solo para carpetas).
        """
        self.selected_path = path
        name = os.path.basename(path)
        if is_file:
            detail = f"Archivo: {name}"
        else:
            detail = f"Carpeta: {name}  ({pdf_count} PDFs)"

        self.label_text.configure(text="Carpeta seleccionada")
        self.label_subtext.configure(text=detail)
        self.label_selected.configure(text="✓ Listo para procesar")
        self.btn_clear.configure(state=tk.NORMAL)

        # Notificar al padre que hay una selección
        if self.on_drop:
            self.on_drop(path)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_selected_path(self) -> Optional[str]:
        """Retorna la ruta seleccionada o None."""
        return self.selected_path

    def clear_selection(self) -> None:
        """Limpia la selección actual y restaura la UI."""
        self.selected_path = None
        self.label_text.configure(text="Arrastra una carpeta aquí")
        self.label_subtext.configure(text="También puedes arrastrar un archivo PDF individual")
        self.label_selected.configure(text="")
        self.btn_clear.configure(state=tk.NORMAL)
        if self.on_clear:
            self.on_clear()

    def configure(self, **kwargs) -> None:
        """Override para manejar state changes."""
        state = kwargs.pop("state", None)
        super().configure(**kwargs)
        if state is not None:
            btn_state = tk.NORMAL if state == tk.NORMAL else tk.DISABLED
            self.btn_select.configure(state=btn_state)
            self.btn_clear.configure(state=btn_state)
