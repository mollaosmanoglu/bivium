from typing import Any

from pydantic import BaseModel


class CameraPosition(BaseModel):
    lat: float
    lng: float
    altitude: float


class SubRegion(BaseModel):
    name: str
    countries: list[str]


class Faction(BaseModel):
    name: str
    color: str
    leader: str
    description: str
    sub_regions: list[SubRegion]


class TimelineStep(BaseModel):
    year: int
    narration: str
    camera: CameraPosition
    factions: list[Faction]


class AlternateTimeline(BaseModel):
    title: str
    steps: list[TimelineStep]


# --- Response models (with merged GeoJSON) ---


class FactionInfo(BaseModel):
    name: str
    color: str
    leader: str
    description: str
    lat: float
    lng: float


class MergedRegion(BaseModel):
    faction_name: str
    region_name: str
    color: str
    geometry: dict[str, Any]


class GeoStep(BaseModel):
    year: int
    narration: str
    camera: CameraPosition
    factions: list[FactionInfo]
    regions: list[MergedRegion]


class GeoTimeline(BaseModel):
    title: str
    steps: list[GeoStep]
