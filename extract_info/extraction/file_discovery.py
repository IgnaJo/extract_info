"""Descubrimiento recursivo de documentos PDF."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredFile:
    """PDF encontrado y su ruta relativa a la carpeta raíz."""

    path: str
    relative_path: str


def discover_pdf_files(root_path: str) -> list[DiscoveredFile]:
    """Encuentra PDFs descendientes de una carpeta sin duplicar enlaces."""
    root_path = os.path.abspath(root_path)
    discovered: list[DiscoveredFile] = []
    visited_directories: set[str] = set()
    visited_files: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=True):
        real_dir = os.path.realpath(dirpath)
        if real_dir in visited_directories:
            dirnames[:] = []
            continue
        visited_directories.add(real_dir)
        dirnames.sort()

        for filename in sorted(filenames):
            if not filename.lower().endswith(".pdf"):
                continue

            path = os.path.join(dirpath, filename)
            if not os.path.isfile(path):
                continue

            real_file = os.path.realpath(path)
            if real_file in visited_files:
                continue
            visited_files.add(real_file)

            relative_path = os.path.relpath(path, root_path).replace(os.sep, "/")
            discovered.append(DiscoveredFile(path=path, relative_path=relative_path))

    discovered.sort(key=lambda item: item.relative_path)
    return discovered
