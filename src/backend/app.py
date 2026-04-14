import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from shapely.geometry import shape

from src.backend.agent import (
    chat_with_leader,
    generate_timeline,
    stream_timeline_chunks,
)
from src.backend.geo import merge_countries
from src.backend.models import (
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


class ChatRequest(BaseModel):
    question: str
    timeline_title: str
    step_year: int
    step_narration: str
    faction_name: str
    leader: str
    government_type: str
    capital: str
    message: str
    history: list[dict[str, str]]


# Geographic regions with muted colors for unassigned countries
GEO_REGIONS: dict[str, tuple[list[str], str]] = {
    "North America": (
        [
            "USA",
            "CAN",
            "MEX",
            "GTM",
            "BLZ",
            "SLV",
            "HND",
            "NIC",
            "CRI",
            "PAN",
            "CUB",
            "JAM",
            "HTI",
            "DOM",
            "BHS",
            "TTO",
            "PRI",
        ],
        "#2a2a3e",
    ),
    "South America": (
        [
            "BRA",
            "ARG",
            "CHL",
            "COL",
            "VEN",
            "PER",
            "ECU",
            "BOL",
            "PRY",
            "URY",
            "GUY",
            "SUR",
            "FLK",
        ],
        "#2e2a3e",
    ),
    "Western Europe": (
        [
            "GBR",
            "FRA",
            "DEU",
            "ESP",
            "PRT",
            "ITA",
            "NLD",
            "BEL",
            "CHE",
            "AUT",
            "IRL",
            "LUX",
            "DNK",
            "NOR",
            "SWE",
            "FIN",
            "ISL",
            "GRL",
        ],
        "#2a2e3e",
    ),
    "Eastern Europe": (
        [
            "POL",
            "CZE",
            "SVK",
            "HUN",
            "ROU",
            "BGR",
            "SRB",
            "HRV",
            "BIH",
            "SVN",
            "MNE",
            "MKD",
            "ALB",
            "GRC",
            "XKX",
            "LTU",
            "LVA",
            "EST",
            "BLR",
            "UKR",
            "MDA",
        ],
        "#2d2a3e",
    ),
    "Russia & Central Asia": (
        ["RUS", "KAZ", "UZB", "TKM", "TJK", "KGZ", "MNG", "GEO", "ARM", "AZE"],
        "#302a3e",
    ),
    "Middle East": (
        [
            "TUR",
            "IRQ",
            "IRN",
            "SYR",
            "JOR",
            "LBN",
            "ISR",
            "PSE",
            "KWT",
            "OMN",
            "ARE",
            "YEM",
            "QAT",
            "SAU",
            "BHR",
            "CYP",
        ],
        "#3e2a2a",
    ),
    "North Africa": (
        ["MAR", "DZA", "TUN", "LBY", "EGY", "ESH", "MRT", "SDN"],
        "#352a2a",
    ),
    "West Africa": (
        [
            "SEN",
            "GMB",
            "GIN",
            "GNB",
            "SLE",
            "LBR",
            "CIV",
            "MLI",
            "BFA",
            "NER",
            "GHA",
            "TGO",
            "BEN",
            "NGA",
        ],
        "#2a352a",
    ),
    "Central & East Africa": (
        [
            "CMR",
            "CAF",
            "TCD",
            "COD",
            "COG",
            "GAB",
            "GNQ",
            "KEN",
            "TZA",
            "UGA",
            "RWA",
            "BDI",
            "ETH",
            "ERI",
            "DJI",
            "SOM",
            "SSD",
        ],
        "#2a3e2e",
    ),
    "Southern Africa": (
        ["ZAF", "NAM", "BWA", "ZWE", "ZMB", "MOZ", "MWI", "SWZ", "LSO", "MDG", "AGO"],
        "#2a3a2a",
    ),
    "South Asia": (["IND", "PAK", "BGD", "LKA", "NPL", "BTN", "AFG"], "#3e3a2a"),
    "East Asia": (["CHN", "JPN", "KOR", "PRK", "TWN"], "#2a3a3e"),
    "Southeast Asia & Pacific": (
        [
            "THA",
            "MMR",
            "VNM",
            "LAO",
            "KHM",
            "MYS",
            "IDN",
            "PHL",
            "BRN",
            "TLS",
            "AUS",
            "NZL",
            "PNG",
            "FJI",
            "SLB",
            "VUT",
            "NCL",
        ],
        "#2a3e3a",
    ),
    "Other": (["ATA", "ATF"], "#222233"),
}


def _merge_step(step: TimelineStep, faction_map: dict[str, FactionDef]) -> GeoStep:
    regions: list[MergedRegion] = []
    faction_infos: list[FactionInfo] = []
    assigned: set[str] = set()

    for sf in step.faction_states:
        fdef = faction_map.get(sf.faction_id)
        if not fdef:
            continue
        # Skip unaligned — let geo background handle them
        if sf.government_type == "unaligned" or sf.faction_id == "unaligned":
            continue
        assigned.update(sf.countries)
        geometry = merge_countries(sf.countries)
        if geometry is not None:
            geom = shape(geometry)
            centroid = geom.centroid
            regions.append(
                MergedRegion(
                    faction_name=fdef.name,
                    region_name="",
                    color=fdef.color,
                    geometry=geometry,
                )
            )
            faction_infos.append(
                FactionInfo(
                    name=fdef.name,
                    color=fdef.color,
                    leader=sf.leader,
                    government_type=sf.government_type,
                    capital=sf.capital,
                    description=sf.description,
                    lat=centroid.y,
                    lng=centroid.x,
                )
            )

    # Muted geographic fill for unassigned countries
    for region_name, (codes, color) in GEO_REGIONS.items():
        leftover = [c for c in codes if c not in assigned]
        if not leftover:
            continue
        geometry = merge_countries(leftover)
        if geometry is not None:
            regions.append(
                MergedRegion(
                    faction_name=region_name,
                    region_name="",
                    color=color,
                    geometry=geometry,
                )
            )

    return GeoStep(
        year=step.year,
        narration=step.narration,
        key_events=step.key_events,
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
async def create_timeline_endpoint(req: TimelineRequest) -> GeoTimeline:
    logger.info("Question: %s", req.question)
    start = time.monotonic()
    raw = await generate_timeline(req.question)
    elapsed = time.monotonic() - start
    logger.info("Generated %d steps in %.1fs: %s", len(raw.steps), elapsed, raw.title)
    geo = _merge_timeline(raw)
    logger.info("Merged %d regions", sum(len(s.regions) for s in geo.steps))
    return geo  # type: ignore[return-value]


def _sse(event_type: str, data: object) -> str:
    return f"data: {json.dumps({'type': event_type, **data} if isinstance(data, dict) else {'type': event_type, 'data': data})}\n\n"


async def _stream_timeline(question: str) -> AsyncGenerator[str, None]:
    start = time.monotonic()
    buf = ""
    sent = 0
    title_sent = False
    faction_defs: list[FactionDef] = []
    faction_map: dict[str, FactionDef] = {}

    async for chunk in stream_timeline_chunks(question):
        buf += chunk

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
                yield _sse("step", geo_step.model_dump())
                sent += 1
                logger.info(
                    "Streamed step %d [%d] (%.1fs)",
                    sent,
                    step.year,
                    time.monotonic() - start,
                )

    # Parse any remaining steps from the complete buffer
    if not faction_defs:
        faction_defs = _try_parse_factions(buf)
        faction_map = {f.id: f for f in faction_defs}
    if not title_sent:
        try:
            raw = AlternateTimeline.model_validate_json(buf)
            yield _sse("title", {"title": raw.title})
        except Exception:  # noqa: BLE001
            pass
    parsed = _try_parse_steps(buf)
    for step in parsed[sent:]:
        geo_step = _merge_step(step, faction_map)
        yield _sse("step", geo_step.model_dump())
        sent += 1

    # Log final output summary
    try:
        raw = AlternateTimeline.model_validate_json(buf)
        logger.info("Final output JSON:\n%s", raw.model_dump_json(indent=2))
        for i, step in enumerate(raw.steps):
            codes: set[str] = set()
            for fs in step.faction_states:
                codes.update(fs.countries)
            logger.info(
                "Step %d [%d]: %d entities, %d countries",
                i + 1,
                step.year,
                len(step.faction_states),
                len(codes),
            )
    except Exception:  # noqa: BLE001
        pass

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


async def _stream_chat(req: ChatRequest) -> AsyncGenerator[str, None]:
    async for chunk in chat_with_leader(
        leader=req.leader,
        faction_name=req.faction_name,
        government_type=req.government_type,
        capital=req.capital,
        year=req.step_year,
        title=req.timeline_title,
        narration=req.step_narration,
        message=req.message,
        history=req.history,
    ):
        yield f"data: {json.dumps({'text': chunk})}\n\n"
    yield 'data: {"done": true}\n\n'


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
    logger.info("Chat: %s → %s", req.leader, req.message[:80])
    return StreamingResponse(
        _stream_chat(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
