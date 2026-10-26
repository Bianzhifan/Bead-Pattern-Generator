from __future__ import annotations

import numpy as np


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """Convert sRGB values in [0, 1] to linear RGB."""
    rgb = np.asarray(rgb, dtype=np.float64)

    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def linear_rgb_to_lab_d65(linear_rgb: np.ndarray) -> np.ndarray:
    """Convert linear sRGB (D65) to CIE Lab (D65 reference white)."""
    values = np.asarray(linear_rgb, dtype=np.float64)
    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = values @ matrix.T
    white = np.array([0.95047, 1.0, 1.08883])
    ratio = xyz / white
    delta = 6 / 29
    f = np.where(ratio > delta**3, np.cbrt(ratio), ratio / (3 * delta**2) + 4 / 29)

    l_star = 116 * f[..., 1] - 16
    a_star = 500 * (f[..., 0] - f[..., 1])
    b_star = 200 * (f[..., 1] - f[..., 2])
    return np.stack((l_star, a_star, b_star), axis=-1)


def delta_e_2000(lab: np.ndarray, palette_lab: np.ndarray) -> np.ndarray:
    """Return CIEDE2000 distances for (..., 3) colors against (N, 3) colors."""
    source = np.asarray(lab, dtype=np.float64)[..., None, :]
    target = np.asarray(palette_lab, dtype=np.float64)
    l1, a1, b1 = source[..., 0], source[..., 1], source[..., 2]
    l2, a2, b2 = target[..., 0], target[..., 1], target[..., 2]
    c1 = np.hypot(a1, b1)
    c2 = np.hypot(a2, b2)
    mean_c = (c1 + c2) / 2
    g = 0.5 * (1 - np.sqrt(mean_c**7 / (mean_c**7 + 25**7)))

    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.mod(np.degrees(np.arctan2(b1, a1p)), 360)
    h2p = np.mod(np.degrees(np.arctan2(b2, a2p)), 360)
    delta_l = l2 - l1
    delta_c = c2p - c1p
    hue_delta = h2p - h1p
    hue_delta = np.where(c1p * c2p == 0, 0, hue_delta)
    hue_delta = np.where(hue_delta > 180, hue_delta - 360, hue_delta)
    hue_delta = np.where(hue_delta < -180, hue_delta + 360, hue_delta)
    delta_h = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(hue_delta / 2))

    mean_l = (l1 + l2) / 2
    mean_c_p = (c1p + c2p) / 2
    hue_sum = h1p + h2p
    mean_h = np.where(c1p * c2p == 0, hue_sum, hue_sum / 2)
    mean_h = np.where(np.abs(h1p - h2p) > 180, mean_h + 180, mean_h)
    mean_h = np.mod(mean_h, 360)

    t = (
        1
        - 0.17 * np.cos(np.radians(mean_h - 30))
        + 0.24 * np.cos(np.radians(2 * mean_h))
        + 0.32 * np.cos(np.radians(3 * mean_h + 6))
        - 0.20 * np.cos(np.radians(4 * mean_h - 63))
    )
    delta_theta = 30 * np.exp(-((mean_h - 275) / 25) ** 2)
    r_c = 2 * np.sqrt(mean_c_p**7 / (mean_c_p**7 + 25**7))
    s_l = 1 + 0.015 * (mean_l - 50) ** 2 / np.sqrt(20 + (mean_l - 50) ** 2)
    s_c = 1 + 0.045 * mean_c_p
    s_h = 1 + 0.015 * mean_c_p * t
    r_t = -np.sin(np.radians(2 * delta_theta)) * r_c

    return np.sqrt(
        (delta_l / s_l) ** 2
        + (delta_c / s_c) ** 2
        + (delta_h / s_h) ** 2
        + r_t * (delta_c / s_c) * (delta_h / s_h)
    )


def nearest_palette_indices(grid_lab: np.ndarray, palette_lab: np.ndarray) -> np.ndarray:
    distances = delta_e_2000(grid_lab, palette_lab)

    # Palette colors are sorted by code during startup, so argmin breaks ties deterministically.
    return np.argmin(distances, axis=-1)

