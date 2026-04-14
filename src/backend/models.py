from typing import Any, Literal

from pydantic import BaseModel, Field

GovernmentType = Literal[
    "monarchy",
    "republic",
    "empire",
    "democracy",
    "theocracy",
    "military_junta",
    "communist",
    "fascist",
    "tribal",
    "federation",
    "city_state",
    "protectorate",
    "unaligned",
]


class CameraPosition(BaseModel):
    lat: float
    lng: float
    altitude: float = Field(
        description="Globe radius units. 1.5 = regional, 2.5 = continental."
    )


class EntityDef(BaseModel):
    id: str = Field(
        description="Stable short slug, e.g. 'ottoman', 'british'. Same across all steps."
    )
    name: str = Field(description="Display name, e.g. 'Ottoman Empire'.")
    color: str = Field(
        description="EU4-style saturated hex color. Deep reds, blues, greens, purples. No pastels."
    )


class StepEntity(BaseModel):
    entity_id: str = Field(description="References an entity id. Must match exactly.")
    leader: str = Field(
        description="Historical leader name. Use '-' for unaligned entities."
    )
    description: str = Field(
        description=(
            "A vivid description of this entity's state at this point in time. "
            "Cover its political mood, recent events, and standing in the world. "
            "Write richly; do not be terse."
        )
    )
    government_type: GovernmentType = Field(
        description=(
            "Regime type for THIS step. Pick the closest enum value. "
            "Use 'unaligned' for catch-all/non-state entities."
        )
    )
    capital: str = Field(
        description=(
            "Capital city of this regime in this step's year. Use a real "
            "historical city name (e.g. 'Constantinople' not 'Istanbul' for "
            "the Ottoman Empire). Use '-' for unaligned entities."
        )
    )
    capital_lat: float = Field(description="Latitude of the capital city.")
    capital_lng: float = Field(description="Longitude of the capital city.")
    countries: list[str] = Field(
        description="ISO 3166-1 alpha-3 codes for countries controlled by this entity."
    )


class TimelineStep(BaseModel):
    year: int
    narration: str = Field(
        description=(
            "1-2 punchy headline sentences for this moment — the arc in a "
            "glance. Leave the detailed beats for key_events."
        )
    )
    key_events: list[str] = Field(
        description=(
            "3-5 short bullet points — one sentence each — summarizing the "
            "major events of this step. Factual, specific, and grounded in "
            "the alt-history."
        )
    )
    camera: CameraPosition
    entity_states: list[StepEntity] = Field(
        description="Every entity must appear with its countries. All entities in every step."
    )


class AlternateTimeline(BaseModel):
    title: str = Field(description="Cinematic title for the timeline.")
    entities: list[EntityDef] = Field(
        description="ALL entities across ALL steps. Every sovereign state in the world — empires, kingdoms, republics, city-states."
    )
    steps: list[TimelineStep] = Field(
        description="Exactly 5 chronological steps covering the full alternate history."
    )


# --- Response models (with merged GeoJSON) ---


class EntityInfo(BaseModel):
    name: str
    color: str
    leader: str
    government_type: GovernmentType = "unaligned"
    capital: str = ""
    capital_lat: float = 0.0
    capital_lng: float = 0.0
    description: str
    lat: float
    lng: float


class MergedRegion(BaseModel):
    entity_name: str
    region_name: str
    color: str
    geometry: dict[str, Any]


class GeoStep(BaseModel):
    year: int
    narration: str
    key_events: list[str] = Field(default_factory=list)
    camera: CameraPosition
    entities: list[EntityInfo]
    regions: list[MergedRegion]


class GeoTimeline(BaseModel):
    title: str
    steps: list[GeoStep]
