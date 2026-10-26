from __future__ import annotations

import numpy as np
from PIL import Image

from .color_matching import srgb_to_linear


def _center_crop_to_ratio(image: np.ndarray, width: int, height: int) -> np.ndarray:
    source_height, source_width = image.shape[:2]
    target_ratio = width / height
    source_ratio = source_width / source_height

    if source_ratio > target_ratio:
        crop_width = source_height * target_ratio
        left = (source_width - crop_width) / 2
        return image[:, int(np.floor(left)) : int(np.ceil(left + crop_width))]

    crop_height = source_width / target_ratio
    top = (source_height - crop_height) / 2
    return image[int(np.floor(top)) : int(np.ceil(top + crop_height)), :]


def _overlap_weights(source_size: int, target_size: int) -> np.ndarray:
    """Exact pixel-coverage weights for averaging source pixels into target cells."""
    boundaries = np.linspace(0, source_size, target_size + 1)
    pixel_start = np.arange(source_size)[None, :]
    pixel_end = pixel_start + 1
    cell_start = boundaries[:-1, None]
    cell_end = boundaries[1:, None]
    overlap = np.maximum(0, np.minimum(pixel_end, cell_end) - np.maximum(pixel_start, cell_start))

    return overlap / (cell_end - cell_start)


def area_average_in_linear_rgb(image: Image.Image, width: int, height: int, *, crop: bool) -> np.ndarray:
    """Convert a normalized RGBA sRGB image into a linear-RGB color grid."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float64) / 255
    linear_rgb = srgb_to_linear(rgba[..., :3])
    alpha = rgba[..., 3:4]

    # Composite against white after conversion, where alpha blending is physically meaningful.
    linear_rgb = linear_rgb * alpha + (1 - alpha)
    source = _center_crop_to_ratio(linear_rgb, width, height) if crop else linear_rgb
    source_height, source_width = source.shape[:2]
    horizontal = _overlap_weights(source_width, width)
    vertical = _overlap_weights(source_height, height)

    # Keep the grid in row-major order: (target_height, target_width, RGB).
    return np.einsum("hs,swc,tw->htc", vertical, source, horizontal, optimize=True)

