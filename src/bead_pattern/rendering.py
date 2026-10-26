from __future__ import annotations

from collections import Counter
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .schemas import Palette, PatternGrid


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _text_color(hex_value: str) -> str:
    red, green, blue = (int(hex_value[index : index + 2], 16) for index in (1, 3, 5))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue

    return "#111111" if luminance > 150 else "#FFFFFF"


def render_png(grid: PatternGrid, palette: Palette) -> bytes:
    height, width = grid.color_indices.shape
    cell = max(18, min(30, 1800 // max(width, height)))
    left_margin, top_margin = 42, 44
    grid_width, grid_height = width * cell, height * cell

    used_indices = [index for index, count in enumerate(grid.counts) if count]
    marker_by_index = {index: str(position + 1) for position, index in enumerate(used_indices)}
    columns = 3
    legend_rows = (len(used_indices) + columns - 1) // columns
    legend_height = 36 + legend_rows * 32
    canvas_width = max(left_margin + grid_width + 24, columns * 255 + 32)
    canvas_height = top_margin + grid_height + 24 + legend_height + 20

    image = Image.new("RGB", (canvas_width, canvas_height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    label_font = _font(max(8, min(13, cell // 2)))
    coordinate_font = _font(12)
    legend_font = _font(14)

    draw.text(
        (left_margin, 12),
        f"{palette.registry_id}/{palette.series_id} · {width}×{height}",
        fill="#111111",
        font=coordinate_font,
    )

    for row in range(height):
        for column in range(width):
            index = int(grid.color_indices[row, column])
            color = palette.colors[index]
            x0, y0 = left_margin + column * cell, top_margin + row * cell
            x1, y1 = x0 + cell, y0 + cell
            draw.rectangle((x0, y0, x1, y1), fill=color.hex, outline="#565656", width=1)
            marker = marker_by_index[index]
            marker_box = draw.textbbox((0, 0), marker, font=label_font)
            draw.text(
                (
                    x0 + (cell - (marker_box[2] - marker_box[0])) / 2,
                    y0 + (cell - (marker_box[3] - marker_box[1])) / 2 - 1,
                ),
                marker,
                fill=_text_color(color.hex),
                font=label_font,
            )

        draw.text(
            (4, top_margin + row * cell + max(1, cell // 4)),
            str(row + 1),
            fill="#111111",
            font=coordinate_font,
        )

    for column in range(width):
        draw.text(
            (left_margin + column * cell + max(1, cell // 4), top_margin - 18),
            str(column + 1),
            fill="#111111",
            font=coordinate_font,
        )

    legend_top = top_margin + grid_height + 24
    draw.text((16, legend_top), "Legend", fill="#111111", font=legend_font)

    for position, index in enumerate(used_indices):
        column, row = position % columns, position // columns
        x, y = 16 + column * 255, legend_top + 24 + row * 32
        color = palette.colors[index]
        draw.rectangle((x, y, x + 22, y + 22), fill=color.hex, outline="#333333")
        label = f"{marker_by_index[index]}. {color.code}  {color.name}  ×{int(grid.counts[index])}"
        draw.text((x + 30, y + 3), label, fill="#111111", font=legend_font)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)

    return output.getvalue()

