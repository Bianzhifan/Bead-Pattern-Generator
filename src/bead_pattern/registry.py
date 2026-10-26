from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from .color_matching import linear_rgb_to_lab_d65, srgb_to_linear
from .schemas import Palette, PaletteColor

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
REGISTRY_ROOT = Path(__file__).resolve().parents[1] / "data" / "registries"


class RegistryError(RuntimeError):
    pass


class RegistryIndex:
    def __init__(self, palettes: dict[tuple[str, str], Palette]) -> None:
        self._palettes = palettes

    @classmethod
    def load(cls) -> "RegistryIndex":
        if not REGISTRY_ROOT.is_dir():
            raise RegistryError(f"registry directory is missing: {REGISTRY_ROOT}")

        palettes: dict[tuple[str, str], Palette] = {}

        for path in sorted(REGISTRY_ROOT.glob("*/*.json")):
            registry_id = path.parent.name
            series_id = path.stem
            data = json.loads(path.read_text(encoding="utf-8-sig"))

            if data.get("series_id") != series_id or not isinstance(data.get("name"), str):
                raise RegistryError(f"invalid series metadata in {path}")

            raw_colors = data.get("colors")
            if not isinstance(raw_colors, list) or not raw_colors:
                raise RegistryError(f"colors must be a non-empty array in {path}")

            colors: list[PaletteColor] = []
            seen_codes: set[str] = set()

            for item in raw_colors:
                if not isinstance(item, dict):
                    raise RegistryError(f"invalid color in {path}")

                code, name, hex_value = item.get("code"), item.get("name"), item.get("hex")
                if not all(isinstance(value, str) and value.strip() for value in (code, name, hex_value)):
                    raise RegistryError(f"color fields must be non-empty strings in {path}")
                if code in seen_codes or not HEX_PATTERN.fullmatch(hex_value):
                    raise RegistryError(f"duplicate code or invalid hex in {path}")

                seen_codes.add(code)
                srgb = np.array(
                    [int(hex_value[i : i + 2], 16) for i in (1, 3, 5)], dtype=np.float64
                ) / 255
                linear = srgb_to_linear(srgb)
                colors.append(
                    PaletteColor(code, name, hex_value.upper(), linear, linear_rgb_to_lab_d65(linear))
                )

            colors.sort(key=lambda color: color.code)

            key = (registry_id, series_id)
            if key in palettes:
                raise RegistryError(f"duplicate palette: {registry_id}/{series_id}")

            palettes[key] = Palette(
                registry_id=registry_id,
                series_id=series_id,
                name=data["name"],
                colors=tuple(colors),
                lab_colors=np.stack([color.lab for color in colors]),
            )

        if not palettes:
            raise RegistryError("no palette JSON files found")

        return cls(palettes)

    def get(self, registry_id: str, series_id: str) -> Palette | None:
        return self._palettes.get((registry_id, series_id))

    def registries(self) -> list[dict[str, object]]:
        grouped: dict[str, list[Palette]] = {}
        for palette in self._palettes.values():
            grouped.setdefault(palette.registry_id, []).append(palette)
        return [
            {
                "registry_id": registry_id,
                "series_count": len(palettes),
                "series": [
                    {"series_id": palette.series_id, "name": palette.name, "color_count": len(palette.colors)}
                    for palette in sorted(palettes, key=lambda item: item.series_id)
                ],
            }
            for registry_id, palettes in sorted(grouped.items())
        ]

    def series(self, registry_id: str) -> list[dict[str, object]] | None:
        series = [palette for (registry, _), palette in self._palettes.items() if registry == registry_id]
        if not series:
            return None
        return [
            {"series_id": palette.series_id, "name": palette.name, "color_count": len(palette.colors)}
            for palette in sorted(series, key=lambda item: item.series_id)
        ]

