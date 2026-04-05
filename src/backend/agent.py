from __future__ import annotations

from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrail,
    RunContextWrapper,
    Runner,
)
from agents.items import TResponseInputItem
from pydantic import BaseModel

from src.backend.models import AlternateTimeline

SYSTEM_PROMPT = """\
You are a historian and geopolitics expert. Given a "what if" question about \
alternate history, generate a cinematic timeline of 5-8 steps showing how the \
world would have changed.

Each step has factions — political entities that control groups of modern-day \
countries. Each faction is divided into named sub-regions (provinces, vilayets, \
dominions, etc.) with historical names. This renders as a colored political \
map on a 3D globe (like EU4).

Rules:
- Each step must have a year, a short narration (1-2 sentences), a camera \
position (lat/lng/altitude), and a list of factions.
- Each faction has a name, a color (hex string), and a list of sub_regions.
- Each sub_region has a historical name (e.g. "Vilayet of Syria", \
"Dominion of Egypt", "Province of Rumelia") and a list of modern countries \
it covers using ISO 3166-1 alpha-3 codes.
- Use real ISO_A3 codes. Common ones: TUR, GBR, USA, DEU, FRA, RUS, CHN, \
IND, JPN, BRA, ITA, ESP, EGY, IRQ, SYR, JOR, SAU, IRN, GRC, POL, UKR, etc.
- Split each faction into 2-5 sub-regions with historically plausible names.
- Assign distinct colors per faction. Use saturated, EU4-style colors: \
deep reds, blues, greens, purples, oranges, teals. Avoid pastels.
- Countries NOT in any faction will appear as neutral gray.
- Include 3-6 factions per step covering the relevant region.
- Camera altitude: 1.0 (close) to 3.0 (far). ~1.5 regional, ~2.5 continental.
- Steps should be chronologically ordered.
- Be historically plausible.
- Map modern countries to their historical controllers. E.g., the Ottoman \
Empire at its peak would have sub-regions like "Rumelia" (GRC, BGR, SRB, \
BIH, ALB, MKD), "Anatolia" (TUR), "Mashriq" (SYR, IRQ, JOR, LBN, ISR), \
"Egypt" (EGY, LBY), "Hijaz" (SAU).
"""


class GuardrailOutput(BaseModel):
    is_valid: bool
    reason: str


guardrail_agent: Agent[None] = Agent(
    name="Input Validator",
    model="gpt-4.1-nano",
    instructions=(
        "Determine if the user's input is a valid alternate history 'what if' "
        "question. It should ask about a counterfactual historical scenario. "
        "Reject nonsense, harmful content, or non-historical questions."
    ),
    output_type=GuardrailOutput,
)


async def whatif_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent[Any],
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    text = input if isinstance(input, str) else str(input)
    result = await Runner.run(guardrail_agent, text)
    output: GuardrailOutput = result.final_output  # type: ignore[assignment]
    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=not output.is_valid,
    )


historian: Agent[None] = Agent(
    name="Historian",
    model="gpt-5.4",
    instructions=SYSTEM_PROMPT,
    output_type=AlternateTimeline,
    input_guardrails=[InputGuardrail(guardrail_function=whatif_guardrail)],
)
