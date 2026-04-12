"""Benchmark: Gemini Flash vs GPT-5.4-mini vs GPT-5.4-nano on timeline generation."""

import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from google import genai  # noqa: E402
from google.genai import types as gtypes  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

from src.backend.agent import _build_instructions  # noqa: E402
from src.backend.models import AlternateTimeline  # noqa: E402

QUESTION = "What if the Ottoman Empire never fell?"

# ── Gemini helper ─────────────────────────────────────────────────
gclient = genai.Client()


async def run_gemini(model: str) -> dict:
    instructions = _build_instructions()
    config = gtypes.GenerateContentConfig(
        system_instruction=instructions,
        response_mime_type="application/json",
        response_schema=AlternateTimeline,
        max_output_tokens=32768,
    )
    t0 = time.monotonic()
    resp = await gclient.aio.models.generate_content(
        model=model,
        contents=QUESTION,
        config=config,
    )
    elapsed = time.monotonic() - t0
    text = resp.text or ""
    try:
        raw = AlternateTimeline.model_validate_json(text)
        return _score(model, elapsed, raw)
    except Exception as e:
        return {"model": model, "time": round(elapsed, 1), "error": str(e)[:200]}


# ── OpenAI helper ─────────────────────────────────────────────────
oai = AsyncOpenAI()


def _prepare_openai_schema(schema: dict) -> dict:
    """Resolve $refs inline and add additionalProperties: false everywhere."""
    import copy

    defs = schema.pop("$defs", {})

    def resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_name = obj["$ref"].split("/")[-1]
                if ref_name in defs:
                    return resolve(copy.deepcopy(defs[ref_name]))
                return obj
            return {k: resolve(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve(item) for item in obj]
        return obj

    schema = resolve(schema)

    def add_ap_false(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "object" or "properties" in obj:
                obj["additionalProperties"] = False
            for v in obj.values():
                add_ap_false(v)
        elif isinstance(obj, list):
            for item in obj:
                add_ap_false(item)

    add_ap_false(schema)
    return schema


async def run_openai(model: str) -> dict:
    instructions = _build_instructions()
    schema = AlternateTimeline.model_json_schema()
    schema = _prepare_openai_schema(schema)
    t0 = time.monotonic()
    resp = await oai.responses.create(
        model=model,
        instructions=instructions,
        input=QUESTION,
        text={
            "format": {
                "type": "json_schema",
                "name": "AlternateTimeline",
                "schema": schema,
                "strict": True,
            }
        },
        max_output_tokens=32768,
    )
    elapsed = time.monotonic() - t0
    text = resp.output_text or ""
    try:
        raw = AlternateTimeline.model_validate_json(text)
        return _score(model, elapsed, raw)
    except Exception as e:
        return {"model": model, "time": round(elapsed, 1), "error": str(e)[:200]}


# ── Scoring ───────────────────────────────────────────────────────
def _score(model: str, elapsed: float, raw: AlternateTimeline) -> dict:
    steps = raw.steps
    factions = raw.factions
    countries_per_step = []
    dupes_per_step = []
    for s in steps:
        codes = []
        for fs in s.faction_states:
            for sr in fs.sub_regions:
                codes.extend(sr.countries)
        countries_per_step.append(len(set(codes)))
        dupes_per_step.append(len(codes) - len(set(codes)))
    avg_narr = sum(len(s.narration) for s in steps) / max(len(steps), 1)
    avg_events = sum(len(s.key_events) for s in steps) / max(len(steps), 1)
    return {
        "model": model,
        "time": round(elapsed, 1),
        "steps": len(steps),
        "factions": len(factions),
        "countries": countries_per_step,
        "duplicates": dupes_per_step,
        "avg_narration_chars": round(avg_narr),
        "avg_key_events": round(avg_events, 1),
        "title": raw.title,
    }


# ── Main ──────────────────────────────────────────────────────────
async def main():
    tasks = [
        run_gemini("gemini-3-flash-preview"),
        run_openai("gpt-5.4-mini"),
        run_openai("gpt-5.4-nano"),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    for r in results:
        if isinstance(r, Exception):
            print(f"\nERROR: {r}")
            continue
        print(f"\n── {r['model']} ──")
        if "error" in r:
            print(f"  Time:  {r['time']}s")
            print(f"  ERROR: {r['error']}")
            continue
        print(f"  Time:       {r['time']}s")
        print(f"  Title:      {r['title']}")
        print(f"  Steps:      {r['steps']}")
        print(f"  Factions:   {r['factions']}")
        print(f"  Countries:  {r['countries']}")
        print(f"  Duplicates: {r['duplicates']}")
        print(f"  Avg narr:   {r['avg_narration_chars']} chars")
        print(f"  Avg events: {r['avg_key_events']}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
