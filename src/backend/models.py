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


class SubRegion(BaseModel):
    name: str = Field(
        description="Period-accurate historical name, e.g. 'Eyalet of Rumelia', not 'Balkans'."
    )
    countries: list[str] = Field(
        description="ISO 3166-1 alpha-3 codes. Max 20 per sub-region — split large groups."
    )


class FactionDef(BaseModel):
    id: str = Field(
        description="Stable short slug, e.g. 'ottoman', 'british'. Same across all steps."
    )
    name: str = Field(description="Display name, e.g. 'Ottoman Empire'.")
    color: str = Field(
        description="EU4-style saturated hex color. Deep reds, blues, greens, purples. No pastels."
    )


class StepFaction(BaseModel):
    faction_id: str = Field(
        description="References a FactionDef.id. Must match exactly."
    )
    leader: str = Field(
        description="Historical leader name. Use '-' for unaligned faction."
    )
    description: str = Field(
        description="One sentence describing this faction's state at this point in time."
    )
    government_type: GovernmentType = Field(
        description=(
            "Regime type for THIS step. Pick the closest enum value. "
            "Use 'unaligned' for catch-all/non-state factions."
        )
    )
    capital: str = Field(
        description=(
            "Capital city of this regime in this step's year. Use a real "
            "historical city name (e.g. 'Constantinople' not 'Istanbul' for "
            "the Ottoman Empire). Use '-' for unaligned factions."
        )
    )
    backstory: str = Field(
        description=(
            "Two to three sentences explaining how this regime came to be in "
            "this step. Ground in the timeline narration; do not contradict it."
        )
    )
    sub_regions: list[SubRegion] = Field(
        description="2-5 sub-regions. Core homeland FIRST. Each max 20 countries."
    )


class TimelineStep(BaseModel):
    year: int
    narration: str = Field(
        description="Cinematic one-paragraph narration of this moment in the timeline."
    )
    camera: CameraPosition
    faction_states: list[StepFaction] = Field(
        description="Every faction active in this step. Must cover ALL countries."
    )


class AlternateTimeline(BaseModel):
    title: str = Field(description="Cinematic title for the timeline.")
    factions: list[FactionDef] = Field(
        description="ALL factions across ALL steps. At least 12. Define once, reference by id."
    )
    steps: list[TimelineStep] = Field(
        description="5-8 chronological steps covering the full alternate history."
    )


# --- Response models (with merged GeoJSON) ---


class FactionInfo(BaseModel):
    name: str
    color: str
    leader: str
    government_type: GovernmentType = "unaligned"
    capital: str = ""
    backstory: str = ""
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
