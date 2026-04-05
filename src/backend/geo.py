from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

logger = logging.getLogger("bivium")

_DATA_DIR = Path(__file__).resolve().parent / "data"
_COUNTRIES_PATH = (
    _DATA_DIR.parent.parent / "frontend" / "public" / "data" / "countries-110m.geojson"
)
_PROVINCES_PATH = _DATA_DIR / "provinces.geojson"

_country_geometries: dict[str, Any] = {}
_provinces_by_country: dict[str, list[dict[str, Any]]] = {}


def _load() -> None:
    if _country_geometries:
        return

    # Load country-level geometries (fallback)
    with open(_COUNTRIES_PATH) as f:
        data = json.load(f)
    for feat in data["features"]:
        iso = feat["properties"]["ISO_A3"]
        _country_geometries[iso] = shape(feat["geometry"])
    logger.info("Loaded %d country geometries", len(_country_geometries))

    # Load province-level geometries
    if _PROVINCES_PATH.exists():
        with open(_PROVINCES_PATH) as f:
            pdata = json.load(f)
        for feat in pdata["features"]:
            iso2 = feat["properties"].get("iso_a2", "")
            name = feat["properties"].get("name", "")
            if iso2 and name:
                _provinces_by_country.setdefault(iso2, []).append(
                    {"name": name, "geometry": shape(feat["geometry"])}
                )
        logger.info("Loaded provinces for %d countries", len(_provinces_by_country))


def merge_countries(iso_codes: list[str]) -> dict[str, Any] | None:
    """Merge multiple country geometries into one GeoJSON geometry."""
    _load()
    geoms = [
        _country_geometries[iso] for iso in iso_codes if iso in _country_geometries
    ]
    if not geoms:
        return None
    merged = unary_union(geoms)
    if not merged.is_valid:
        merged = merged.buffer(0)
    if merged.is_empty:
        return None
    return mapping(merged)  # type: ignore[return-value]
