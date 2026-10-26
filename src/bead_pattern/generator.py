from __future__ import annotations

import numpy as np
from PIL import Image

from .color_matching import linear_rgb_to_lab_d65, nearest_palette_indices
from .image_processing import area_average_in_linear_rgb
from .rendering import render_png
from .schemas import Palette, PatternGrid


def generate(validated_image: Image.Image, palette: Palette, width: int, height: int, *, crop: bool) -> bytes:
    grid_rgb = area_average_in_linear_rgb(validated_image, width, height, crop=crop)
    grid_lab = linear_rgb_to_lab_d65(grid_rgb)
    color_indices = nearest_palette_indices(grid_lab, palette.lab_colors)
    counts = np.bincount(color_indices.ravel(), minlength=len(palette.colors))

    return render_png(PatternGrid(color_indices=color_indices, counts=counts), palette)

