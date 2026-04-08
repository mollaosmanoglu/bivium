import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

from agents import (  # noqa: E402
    InputGuardrailTripwireTriggered,
    Runner,
    enable_verbose_stdout_logging,
)

enable_verbose_stdout_logging()  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from openai.types.responses import ResponseTextDeltaEvent  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from shapely.geometry import shape  # noqa: E402

from src.backend.agent import historian  # noqa: E402
from src.backend.geo import merge_countries  # noqa: E402
from src.backend.models import (  # noqa: E402
    AlternateTimeline,
    FactionDef,
    FactionInfo,
    GeoStep,
    GeoTimeline,
    MergedRegion,
    TimelineStep,
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


def _merge_step(step: TimelineStep, faction_map: dict[str, FactionDef]) -> GeoStep:
    regions: list[MergedRegion] = []
    faction_infos: list[FactionInfo] = []
    for sf in step.faction_states:
        fdef = faction_map.get(sf.faction_id)
        if not fdef:
            continue
        faction_geoms: list[Any] = []
        n = len(sf.sub_regions)
        for i, sub in enumerate(sf.sub_regions):
            shade_factor = 1.0 + (i * 0.15 / max(1, n - 1)) if n > 1 else 1.0
            color = _shade(fdef.color, shade_factor)
            geometry = merge_countries(sub.countries)
            if geometry is not None:
                faction_geoms.append(shape(geometry))
                regions.append(
                    MergedRegion(
                        faction_name=fdef.name,
                        region_name=sub.name,
                        color=color,
                        geometry=geometry,
                    )
                )
        # Compute centroid from first sub-region (homeland/core)
        if faction_geoms:
            centroid = faction_geoms[0].centroid
            lat, lng = centroid.y, centroid.x
        else:
            lat, lng = 0.0, 0.0
        faction_infos.append(
            FactionInfo(
                name=fdef.name,
                color=fdef.color,
                leader=sf.leader,
                description=sf.description,
                lat=lat,
                lng=lng,
            )
        )
    return GeoStep(
        year=step.year,
        narration=step.narration,
        camera=step.camera,
        factions=faction_infos,
        regions=regions,
    )


def _merge_timeline(raw: AlternateTimeline) -> GeoTimeline:
    faction_map = {f.id: f for f in raw.factions}
    return GeoTimeline(
        title=raw.title,
        steps=[_merge_step(step, faction_map) for step in raw.steps],
    )


def _extract_array_objects(buf: str, key: str) -> list[str]:
    """Extract complete JSON object strings from an array field in a buffer."""
    idx = buf.find(f'"{key}"')
    if idx == -1:
        return []
    bracket = buf.find("[", idx)
    if bracket == -1:
        return []

    objects: list[str] = []
    depth = 0
    start = -1
    i = bracket + 1
    while i < len(buf):
        ch = buf[i]
        if ch == '"':
            i += 1
            while i < len(buf) and buf[i] != '"':
                if buf[i] == "\\":
                    i += 1
                i += 1
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                objects.append(buf[start : i + 1])
                start = -1
        elif ch == "]" and depth == 0:
            break
        i += 1
    return objects


def _try_parse_factions(buf: str) -> list[FactionDef]:
    """Extract FactionDef objects from the top-level factions array.

    Only parses once "steps" key appears — that guarantees the factions
    array is fully streamed.
    """
    if '"steps"' not in buf:
        return []
    factions: list[FactionDef] = []
    steps_idx = buf.find('"steps"')
    for obj_str in _extract_array_objects(buf[:steps_idx], "factions"):
        try:
            factions.append(FactionDef.model_validate_json(obj_str))
        except Exception:  # noqa: BLE001
            pass
    return factions


def _try_parse_steps(buf: str) -> list[TimelineStep]:
    """Extract complete TimelineStep objects from the steps array."""
    steps: list[TimelineStep] = []
    for obj_str in _extract_array_objects(buf, "steps"):
        try:
            steps.append(TimelineStep.model_validate_json(obj_str))
        except Exception:  # noqa: BLE001
            pass
    return steps


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
    geo = _merge_timeline(raw)
    logger.info("Merged %d regions", sum(len(s.regions) for s in geo.steps))
    return geo  # type: ignore[return-value]


def _sse(event_type: str, data: object) -> str:
    return f"data: {json.dumps({'type': event_type, **data} if isinstance(data, dict) else {'type': event_type, 'data': data})}\n\n"


async def _stream_timeline(question: str) -> AsyncGenerator[str, None]:
    start = time.monotonic()
    result = Runner.run_streamed(historian, question)
    buf = ""
    sent = 0
    title_sent = False
    faction_defs: list[FactionDef] = []
    faction_map: dict[str, FactionDef] = {}

    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            buf += event.data.delta

            # Send title as soon as we can parse it
            if not title_sent:
                ti = buf.find('"title"')
                if ti != -1:
                    colon = buf.find(":", ti)
                    if colon != -1:
                        q1 = buf.find('"', colon + 1)
                        if q1 != -1:
                            q2 = q1 + 1
                            while q2 < len(buf) and buf[q2] != '"':
                                if buf[q2] == "\\":
                                    q2 += 1
                                q2 += 1
                            if q2 < len(buf):
                                title = buf[q1 + 1 : q2]
                                yield _sse("title", {"title": title})
                                title_sent = True
                                logger.info("Streamed title: %s", title)

            # Parse factions once (they come before steps in the JSON)
            if not faction_defs:
                faction_defs = _try_parse_factions(buf)
                if faction_defs:
                    faction_map = {f.id: f for f in faction_defs}
                    logger.info("Parsed %d faction defs", len(faction_defs))

            # Try to parse completed steps
            if faction_map:
                parsed = _try_parse_steps(buf)
                for step in parsed[sent:]:
                    geo_step = _merge_step(step, faction_map)
                    yield _sse("step", json.loads(geo_step.model_dump_json()))
                    sent += 1
                    logger.info(
                        "Streamed step %d [%d] (%.1fs)",
                        sent,
                        step.year,
                        time.monotonic() - start,
                    )

    # Send any remaining steps from final output
    if result.final_output:
        raw: AlternateTimeline = result.final_output  # type: ignore[assignment]
        logger.info("Final output JSON:\n%s", raw.model_dump_json(indent=2))
        faction_map = {f.id: f for f in raw.factions}
        if not title_sent:
            yield _sse("title", {"title": raw.title})
        for step in raw.steps[sent:]:
            geo_step = _merge_step(step, faction_map)
            yield _sse("step", json.loads(geo_step.model_dump_json()))
            sent += 1

    elapsed = time.monotonic() - start
    logger.info("Stream complete: %d steps in %.1fs", sent, elapsed)
    yield _sse("done", {})


@app.post("/api/timeline/stream")
async def stream_timeline(req: TimelineRequest) -> StreamingResponse:
    logger.info("Stream question: %s", req.question)
    return StreamingResponse(
        _stream_timeline(req.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
