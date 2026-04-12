from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.models import TimelineStep

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
    # Natural Earth uses -99 for France, Norway, etc. Map by name instead.
    _name_to_iso: dict[str, str] = {
        "France": "FRA",
        "Norway": "NOR",
        "N. Cyprus": "CYP",
        "Kosovo": "XKX",
        "Somaliland": "SOM",
    }
    for feat in data["features"]:
        iso = feat["properties"]["ISO_A3"]
        name = feat["properties"].get("NAME", "")
        if iso == "-99":
            iso = _name_to_iso.get(name, iso)
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


def all_iso_codes() -> set[str]:
    """Return all ISO codes available in the countries GeoJSON."""
    _load()
    return set(_country_geometries.keys())


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


def patch_step_coverage(step: TimelineStep) -> None:
    """Ensure every ISO code is assigned to exactly one faction. Mutates *step*."""
    _load()
    valid = set(_country_geometries.keys())

    # Strip unknown codes and build assignment map: code → [(faction_idx, sub_idx)]
    assignments: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for fi, fs in enumerate(step.faction_states):
        for si, sr in enumerate(fs.sub_regions):
            sr.countries = [c for c in sr.countries if c in valid]
            for c in sr.countries:
                assignments[c].append((fi, si))

    # Deduplicate: keep code in the sub_region whose centroid is nearest
    for code, locs in assignments.items():
        if len(locs) <= 1:
            continue
        country_centroid = _country_geometries[code].centroid
        best = min(
            locs,
            key=lambda loc: _sub_region_centroid(step, loc[0], loc[1]).distance(
                country_centroid
            ),
        )
        for loc in locs:
            if loc != best:
                step.faction_states[loc[0]].sub_regions[loc[1]].countries.remove(code)

    # Fill gaps: assign missing codes to nearest faction's first sub_region
    assigned = {
        c for fs in step.faction_states for sr in fs.sub_regions for c in sr.countries
    }
    missing = valid - assigned
    if not missing:
        return

    # Pre-compute homeland centroids (first sub_region of each faction)
    homeland_centroids: list[tuple[int, Any]] = []
    for fi, fs in enumerate(step.faction_states):
        if fs.sub_regions and fs.sub_regions[0].countries:
            homeland_centroids.append((fi, _sub_region_centroid(step, fi, 0)))
    if not homeland_centroids:
        return

    for code in missing:
        country_centroid = _country_geometries[code].centroid
        best_fi: int
        best_fi, _ = min(
            homeland_centroids,
            key=lambda fc: fc[1].distance(country_centroid),
        )
        step.faction_states[best_fi].sub_regions[0].countries.append(code)


def _sub_region_centroid(step: TimelineStep, fi: int, si: int) -> Any:
    """Compute centroid of a sub_region from its country geometries."""
    codes = step.faction_states[fi].sub_regions[si].countries
    geoms = [_country_geometries[c] for c in codes if c in _country_geometries]
    if geoms:
        return unary_union(geoms).centroid
    return _country_geometries[next(iter(_country_geometries))].centroid
