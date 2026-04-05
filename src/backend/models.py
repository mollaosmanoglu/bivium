from pydantic import BaseModel


class CameraPosition(BaseModel):
    lat: float
    lng: float
    altitude: float


class Faction(BaseModel):
    name: str
    color: str
    countries: list[str]


class TimelineStep(BaseModel):
    year: int
    narration: str
    camera: CameraPosition
    factions: list[Faction]


class AlternateTimeline(BaseModel):
    title: str
    steps: list[TimelineStep]
