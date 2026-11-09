# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller spec para Extractor de Metadatos PDF (onefile)."""

from pathlib import Path

# Rutas base - SPECPATH lo define PyInstaller con la carpeta del spec
BASE_DIR = Path(SPECPATH)
ASSETS_DIR = BASE_DIR / "assets"

# Archivos de datos a incluir (tupla: origen, destino)
datas = [
    (str(ASSETS_DIR / "styles" / "style.QSS"), "assets/styles"),
    (str(ASSETS_DIR / "extract_info.ico"), "assets"),
]

# Falla el build si falta un asset en vez de generar un exe roto
for _src, _dst in datas:
    if not Path(_src).is_file():
        raise SystemExit(f"Falta un archivo requerido por el build: {_src}")

# Hidden imports necesarios para PySide6 y módulos internos
hiddenimports = [
    # PySide6
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
    # Módulos internos
    "extract_info.pipelines.base",
    "extract_info.pipelines.retail",
    "extract_info.pipelines.aseguradora",
    "extract_info.extraction.text_reader",
    "extract_info.extraction.anchors",
    "extract_info.extraction.patterns",
    "extract_info.extraction.validators",
    "extract_info.extraction.file_discovery",
    "extract_info.models",
    "extract_info.pipeline",
    "extract_info.batch",
    "extract_info.csv_writer",
    # Dependencias
    "fitz",
    "pydantic",
]

# Excluir módulos innecesarios para reducir tamaño
excludes = [
    "tkinter",
    "tkinterdnd2",
    "matplotlib",
    "numpy",
    "scipy",
    "PIL",
    "cv2",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "pytest_qt",
    "pyinstaller",
]

# Análisis del script principal
a = Analysis(
    [str(BASE_DIR / "extract_info" / "gui" / "__main__.py")],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Filtrar binarios/datos innecesarios
a.datas = [x for x in a.datas if not any(ex in x[0] for ex in ["__pycache__", ".pyc"])]

# PYZ (Python ZIP)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Ejecutable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="extract_info",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX no es requerido; activarlo solo si está instalado
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # True para debug, False para release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_DIR / "extract_info.ico"),
)