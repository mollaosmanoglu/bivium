import logging
import time

from dotenv import load_dotenv

load_dotenv(override=True)

from agents import InputGuardrailTripwireTriggered, Runner  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from src.backend.agent import historian  # noqa: E402
from src.backend.geo import merge_countries  # noqa: E402
from src.backend.models import (  # noqa: E402
    AlternateTimeline,
    GeoStep,
    GeoTimeline,
    MergedRegion,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bivium")

app = FastAPI()

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class TimelineRequest(BaseModel):
    question: str


def _shade(hex_color: str, factor: float) -> str:
    """Lighten (factor > 1) or darken (factor < 1) a hex color."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _merge_timeline(raw: AlternateTimeline) -> GeoTimeline:
    geo_steps: list[GeoStep] = []
    for step in raw.steps:
        regions: list[MergedRegion] = []
        for faction in step.factions:
            n = len(faction.sub_regions)
            for i, sub in enumerate(faction.sub_regions):
                # Vary shade: first sub-region gets base color, rest get lighter
                shade_factor = 1.0 + (i * 0.15 / max(1, n - 1)) if n > 1 else 1.0
                color = _shade(faction.color, shade_factor)
                geometry = merge_countries(sub.countries)
                if geometry is not None:
                    regions.append(
                        MergedRegion(
                            faction_name=faction.name,
                            region_name=sub.name,
                            color=color,
                            geometry=geometry,
                        )
                    )
        geo_steps.append(
            GeoStep(
                year=step.year,
                narration=step.narration,
                camera=step.camera,
                regions=regions,
            )
        )
    return GeoTimeline(title=raw.title, steps=geo_steps)


@app.post("/api/timeline")
async def create_timeline(req: TimelineRequest) -> GeoTimeline:
    logger.info("Question: %s", req.question)
    start = time.monotonic()
    try:
        result = await Runner.run(historian, req.question)
    except InputGuardrailTripwireTriggered as err:
        logger.warning("Guardrail rejected: %s", req.question)
        raise HTTPException(
            status_code=400, detail="Not a valid what-if question."
        ) from err
    raw: AlternateTimeline = result.final_output  # type: ignore[assignment]
    elapsed = time.monotonic() - start
    logger.info("Generated %d steps in %.1fs: %s", len(raw.steps), elapsed, raw.title)
    for i, step in enumerate(raw.steps):
        for faction in step.factions:
            subs = ", ".join(
                f"{s.name}({len(s.countries)})" for s in faction.sub_regions
            )
            logger.info("  Step %d [%d] %s: %s", i, step.year, faction.name, subs)

    geo = _merge_timeline(raw)
    logger.info("Merged %d regions", sum(len(s.regions) for s in geo.steps))
    return geo
