"""Motor de búsqueda por anclajes con proximidad espacial."""

from __future__ import annotations

import re

from extract_info.extraction.text_reader import PageData, TextBlock


def find_anchor(blocks: list[TextBlock], pattern: re.Pattern) -> tuple[TextBlock, re.Match] | None:
    """Busca un anclaje (etiqueta) en los bloques de texto."""
    for block in blocks:
        match = pattern.search(block.text)
        if match:
            return block, match
    return None


def extract_value_after_anchor(
    blocks: list[TextBlock],
    anchor_pattern: re.Pattern,
    value_group: int = 1,
) -> str | None:
    """Extrae el valor adyacente a un anclaje (legacy, mantener compatibilidad)."""
    result = find_anchor(blocks, anchor_pattern)
    if result is None:
        return None

    block, match = result

    if match.lastindex and match.lastindex >= value_group:
        value = match.group(value_group)
        if value and value.strip():
            return value.strip()

    match_end = match.end()
    remaining = block.text[match_end:].strip()
    if remaining:
        return remaining.split("\n")[0].strip()

    idx = blocks.index(block)
    if idx + 1 < len(blocks):
        next_block = blocks[idx + 1]
        if next_block.top - block.bottom < 30:
            return next_block.text.strip()

    return None


def find_horizontal_neighbor(
    blocks: list[TextBlock],
    label_block: TextBlock,
    label_match: re.Match,
    max_horizontal_dist: float = 200.0,
    max_vertical_diff: float = 10.0,
) -> TextBlock | None:
    """Busca un bloque vecino horizontal (misma fila, a la derecha) del label.

    Para layouts de 2 columnas donde el label está a la izquierda y el valor a la derecha
    en la misma línea/fila (mismo Y, diferente X).
    """
    label_center_y = (label_block.top + label_block.bottom) / 2
    # Use label block's left edge as reference, not right edge
    # because label might be on left side of a wide block
    label_x_ref = label_block.left

    candidates = []
    for block in blocks:
        if block is label_block:
            continue

        block_center_y = (block.top + block.bottom) / 2
        vert_diff = abs(block_center_y - label_center_y)

        if vert_diff > max_vertical_diff:
            continue

        # Block should be to the right of label block's left edge
        horiz_dist = block.left - label_x_ref
        if horiz_dist < 5 or horiz_dist > max_horizontal_dist:
            continue

        if block.text.strip():
            candidates.append((horiz_dist, vert_diff, block))

    candidates.sort(key=lambda c: (c[0], c[1]))

    if candidates:
        return candidates[0][2]
    return None


def find_value_near_label(
    blocks: list[TextBlock],
    label_pattern: re.Pattern,
    value_pattern: re.Pattern | None = None,
    max_vertical_dist: float = 80.0,
    prefer_right: bool = True,
    search_horizontal: bool = True,
) -> tuple[str | None, TextBlock | None]:
    """Busca un valor cercano a un label usando proximidad espacial.

    Estrategia (en orden):
    1. Buscar en la misma línea a la derecha del label (texto después del match)
    2. Buscar vecino horizontal (misma fila, a la derecha) - NUEVO
    3. Buscar en bloques cercanos verticalmente (arriba/abajo)
    4. Si value_pattern se provee, aplicar regex sobre el texto encontrado

    Returns:
        Tupla (valor_encontrado, bloque_valor) o (None, None)
    """
    label_block = None
    label_match = None

    for block in blocks:
        match = label_pattern.search(block.text)
        if match:
            label_block = block
            label_match = match
            break

    if label_block is None or label_match is None:
        return None, None

    # Estrategia 1: Texto después del label en el mismo bloque
    match_end_in_text = label_match.end()
    text_after_label = label_block.text[match_end_in_text:].strip()

    if prefer_right and text_after_label:
        first_line = text_after_label.lstrip("\n").split("\n")[0].strip()
        if first_line:
            # Skip if the text looks like another label (contains ":" without digits)
            looks_like_label = bool(re.match(r'^[A-Za-záéíóúñÁÉÍÓÚÑ\s]+:', first_line))
            if not looks_like_label:
                return first_line, label_block

    # Estrategia 2: Vecino horizontal (misma Y, a la derecha)
    if search_horizontal:
        h_neighbor = find_horizontal_neighbor(blocks, label_block, label_match)
        if h_neighbor:
            return h_neighbor.text.strip(), h_neighbor

    # Estrategia 3: Vecinos verticales (fallback original)
    label_bottom = label_block.bottom
    label_top = label_block.top
    label_x = label_block.left

    candidates = []
    for block in blocks:
        if block is label_block:
            continue

        vert_dist = min(
            abs(block.top - label_bottom),
            abs(block.bottom - label_top),
        )

        if vert_dist > max_vertical_dist:
            continue

        horiz_overlap = not (block.right < label_x - 50 or block.left > label_block.right + 200)

        candidates.append((vert_dist, horiz_overlap, block))

    candidates.sort(key=lambda c: (not c[1], c[0]))

    for _dist, _overlap, candidate_block in candidates:
        text = candidate_block.text.strip()
        if text:
            return _apply_value_pattern(text, value_pattern), candidate_block

    return None, None


def _apply_value_pattern(text: str, pattern: re.Pattern | None) -> str | None:
    """Aplica un patrón de valor sobre un texto, o retorna el texto limpio."""
    if pattern is None:
        return text.strip()

    match = pattern.search(text)
    if match:
        return match.group(1) if match.lastindex else match.group(0)
    return None


def find_values_block_near_label(
    blocks: list[TextBlock],
    label_pattern: re.Pattern,
    num_values: int = 3,
    max_vertical_dist: float = 80.0,
) -> list[str] | None:
    """Busca un bloque de valores múltiples cercano a un label.

    Útil cuando PROTOCOLIZADO N° y REP N° comparten un bloque de valores
    con 3 elementos (proto, rep, fecha).

    Retorna lista de valores extraídos o None.
    """
    label_block = None
    for block in blocks:
        if label_pattern.search(block.text):
            label_block = block
            break

    if label_block is None:
        return None

    label_center_y = (label_block.top + label_block.bottom) / 2
    label_x = label_block.left

    candidates = []
    for block in blocks:
        if block is label_block:
            continue

        block_center_y = (block.top + block.bottom) / 2
        vert_dist = abs(block_center_y - label_center_y)

        if vert_dist > max_vertical_dist:
            continue

        horiz_close = block.left >= label_x - 50
        if horiz_close:
            candidates.append((vert_dist, block))

    candidates.sort(key=lambda c: c[0])

    for _dist, candidate_block in candidates:
        text = candidate_block.text.strip()
        if text:
            return _parse_values_block(text, num_values)

    return None


def _parse_values_block(text: str, expected_count: int) -> list[str]:
    """Parsea un bloque de texto con múltiples valores separados por espacios/newlines."""
    parts = re.split(r"\s{2,}|\n", text)
    values = [p.strip() for p in parts if p.strip()]

    if len(values) >= expected_count:
        return values[:expected_count]

    return values if values else []


def search_in_pages(
    pages: list[PageData],
    anchor_pattern: re.Pattern,
    page_indices: list[int] | None = None,
) -> tuple[str, int] | None:
    """Busca un anclaje en múltiples páginas. Retorna (valor, página)."""
    indices = page_indices if page_indices is not None else range(len(pages))
    for idx in indices:
        if idx >= len(pages):
            continue
        page = pages[idx]
        value = extract_value_after_anchor(page.blocks, anchor_pattern)
        if value:
            return value, page.page_number
    return None
