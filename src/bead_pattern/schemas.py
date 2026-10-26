from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class PaletteColor:
    code: str
    name: str
    hex: str
    linear_rgb: np.ndarray
    lab: np.ndarray


@dataclass(frozen=True, slots=True)
class Palette:
    registry_id: str
    series_id: str
    name: str
    colors: tuple[PaletteColor, ...]
    lab_colors: np.ndarray


@dataclass(frozen=True, slots=True)
class PatternGrid:
    color_indices: np.ndarray
    counts: np.ndarray

