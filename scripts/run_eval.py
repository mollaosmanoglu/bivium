"""Run eval scenarios as Phoenix experiments.

Usage:
    .venv/bin/python scripts/run_eval.py --list
    .venv/bin/python scripts/run_eval.py --id ottoman_never_fell
    .venv/bin/python scripts/run_eval.py --all

Reads scenarios from tests/scenarios.yaml and runs the Gemini model.
Results and traces are visible in the Phoenix dashboard at localhost:6006.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dotenv

dotenv.load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402
from phoenix.client import AsyncClient, Client  # noqa: E402
from phoenix.otel import register as _register  # noqa: E402

_register(
    project_name="bivium-eval",
    endpoint="http://localhost:6006/v1/traces",
    batch=True,
    auto_instrument=True,
)

from src.backend.agent import generate_timeline  # noqa: E402
from src.backend.geo import all_iso_codes  # noqa: E402

SCENARIOS_PATH = Path(__file__).resolve().parent.parent / "tests" / "scenarios.yaml"
ALL_ISO = all_iso_codes()


# ── Task ────────────────────────────────────────────────────────────


async def task(input: dict[str, Any]) -> dict[str, Any]:
    """Run the model and extract metrics from the output."""
    question: str = input["input"]
    timeline = await generate_timeline(question)

    faction_ids = [f.id for f in timeline.factions]
    countries_per_step: list[int] = []
    duplicates_per_step: list[int] = []
    max_subregion_size: int = 0
    total_step_factions = 0
    incomplete_enrichments = 0

    for step in timeline.steps:
        codes: list[str] = []
        for fs in step.faction_states:
            total_step_factions += 1
            if not fs.government_type or not fs.capital or not fs.backstory:
                incomplete_enrichments += 1
            for sr in fs.sub_regions:
                max_subregion_size = max(max_subregion_size, len(sr.countries))
                codes.extend(sr.countries)
        countries_per_step.append(len(set(codes)))
        duplicates_per_step.append(len(codes) - len(set(codes)))

    return {
        "faction_count": len(timeline.factions),
        "faction_ids": faction_ids,
        "steps": len(timeline.steps),
        "countries_per_step": countries_per_step,
        "min_countries": min(countries_per_step) if countries_per_step else 0,
        "duplicates_per_step": duplicates_per_step,
        "max_subregion_size": max_subregion_size,
        "total_step_factions": total_step_factions,
        "incomplete_enrichments": incomplete_enrichments,
        "title": timeline.title,
    }


# ── Evaluators ──────────────────────────────────────────────────────


def faction_count(output: Any, expected: Any) -> dict[str, Any]:
    """Check minimum faction count."""
    actual = output.get("faction_count", 0)
    minimum = expected.get("min_factions", 10)
    if actual >= minimum:
        return {
            "score": 1.0,
            "label": "PASS",
            "explanation": f"{actual} factions (>= {minimum})",
        }
    return {
        "score": actual / minimum,
        "label": "FAIL",
        "explanation": f"{actual} factions (< {minimum})",
    }


def country_coverage(output: Any, expected: Any) -> dict[str, Any]:
    """Check minimum country coverage per step."""
    min_countries = output.get("min_countries", 0)
    threshold = expected.get("min_countries_per_step", 160)
    if min_countries >= threshold:
        return {
            "score": 1.0,
            "label": "PASS",
            "explanation": f"{min_countries}/173 countries (>= {threshold})",
        }
    return {
        "score": min_countries / 173,
        "label": "FAIL",
        "explanation": f"{min_countries}/173 countries (< {threshold})",
    }


def no_duplicate_countries(output: Any, expected: Any) -> dict[str, Any]:
    """Check no ISO code appears in multiple factions in a single step."""
    dupes = output.get("duplicates_per_step", [])
    total_dupes = sum(dupes)
    if total_dupes == 0:
        return {"score": 1.0, "label": "PASS", "explanation": "no duplicates"}
    return {
        "score": 0.0,
        "label": "FAIL",
        "explanation": f"{total_dupes} duplicate assignments",
    }


def no_lazy_blobs(output: Any, expected: Any) -> dict[str, Any]:
    """Check no sub-region has > 30 countries."""
    max_size = output.get("max_subregion_size", 0)
    if max_size <= 30:
        return {
            "score": 1.0,
            "label": "PASS",
            "explanation": f"max sub-region: {max_size} countries",
        }
    return {
        "score": 0.0,
        "label": "FAIL",
        "explanation": f"lazy blob: {max_size} countries in one sub-region",
    }


def required_factions(output: Any, expected: Any) -> dict[str, Any]:
    """Check that required faction IDs are present."""
    required = set(expected.get("required_faction_ids", []))
    if not required:
        return {
            "score": 1.0,
            "label": "PASS",
            "explanation": "no required factions specified",
        }
    actual = set(output.get("faction_ids", []))
    missing = required - actual
    if not missing:
        return {
            "score": 1.0,
            "label": "PASS",
            "explanation": "all required factions present",
        }
    return {
        "score": 0.0,
        "label": "FAIL",
        "explanation": f"missing factions: {', '.join(sorted(missing))}",
    }


def enrichment_completeness(output: Any, expected: Any) -> dict[str, Any]:
    """Check every step-faction has government_type, capital, and backstory."""
    total = output.get("total_step_factions", 0)
    incomplete = output.get("incomplete_enrichments", 0)
    if total == 0:
        return {"score": 1.0, "label": "PASS", "explanation": "no factions"}
    rate = (total - incomplete) / total
    threshold = expected.get("min_enrichment_completeness", 1.0)
    label = "PASS" if rate >= threshold else "FAIL"
    return {
        "score": rate,
        "label": label,
        "explanation": (
            f"{total - incomplete}/{total} fully enriched "
            f"({rate:.0%}, need {threshold:.0%})"
        ),
    }


# ── Phoenix setup ───────────────────────────────────────────────────


def upload_dataset(px: Client, scenarios: list[dict[str, Any]]) -> Any:
    """Upload scenarios as a Phoenix dataset."""
    examples = [
        {
            "input": {"input": s["input"], "scenario_id": s["id"]},
            "output": s.get("expected", {}),
            "metadata": {"id": s["id"], "desc": s["desc"]},
        }
        for s in scenarios
    ]
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = f"bivium-eval-{ts}"
    return px.datasets.create_dataset(name=name, examples=examples)  # type: ignore[no-any-return]


def find_scenario(
    all_scenarios: dict[str, list[dict[str, Any]]], scenario_id: str
) -> tuple[str, dict[str, Any]]:
    """Find a scenario by ID across all workflows."""
    for workflow, items in all_scenarios.items():
        for item in items:
            if item["id"] == scenario_id:
                return workflow, item
    print(f"Scenario '{scenario_id}' not found")
    sys.exit(1)


# ── CLI ─────────────────────────────────────────────────────────────


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def list_all() -> None:
    for workflow, items in _load(SCENARIOS_PATH).items():
        print(f"\n{workflow}:")
        for item in items:
            print(f"  {item['id']}: {item['desc']}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval scenarios")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="Run a single scenario by ID")
    group.add_argument("--all", action="store_true", help="Run all scenarios")
    group.add_argument("--list", action="store_true", help="List all scenarios")
    args = parser.parse_args()

    if args.list:
        list_all()
        return

    all_scenarios = _load(SCENARIOS_PATH)

    if args.id:
        _workflow, scenario = find_scenario(all_scenarios, args.id)
        selected = [scenario]
    else:
        selected = [s for items in all_scenarios.values() for s in items]

    px_sync = Client()
    dataset = upload_dataset(px_sync, selected)

    px = AsyncClient()
    result = await px.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators={
            "faction_count": faction_count,
            "country_coverage": country_coverage,
            "no_duplicate_countries": no_duplicate_countries,
            "no_lazy_blobs": no_lazy_blobs,
            "required_factions": required_factions,
            "enrichment_completeness": enrichment_completeness,
        },  # type: ignore[arg-type]
        concurrency=3,
        timeout=180,
    )

    fails = 0
    for ev in result["evaluation_runs"]:
        r = dict(ev.result) if isinstance(ev.result, dict) else {}  # type: ignore[arg-type]
        label = str(r.get("label", "ERROR"))
        explanation = str(r.get("explanation", ev.error or ""))
        if label != "PASS":
            fails += 1
        print(f"  {label:5}  {explanation}")

    total = len(result["evaluation_runs"])
    print(f"\n{total - fails}/{total} passed")
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
