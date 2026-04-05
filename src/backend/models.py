from pydantic import BaseModel


class CameraPosition(BaseModel):
    lat: float
    lng: float
    altitude: float


class CountryHighlight(BaseModel):
    iso_a3: str
    color: str
    altitude: float


class TimelineStep(BaseModel):
    year: int
    narration: str
    camera: CameraPosition
    highlights: list[CountryHighlight]


class AlternateTimeline(BaseModel):
    title: str
    steps: list[TimelineStep]
