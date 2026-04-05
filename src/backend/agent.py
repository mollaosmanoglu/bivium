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

Rules:
- Each step must have a year, a short narration (1-2 sentences), a camera \
position (lat/lng/altitude targeting the relevant region), and country \
highlights with ISO 3166-1 alpha-3 codes.
- Use real ISO_A3 country codes (e.g. TUR, GBR, USA, DEU, FRA, RUS, CHN).
- Camera altitude should be between 1.0 (close) and 3.0 (far). Use ~1.5 for \
regional views, ~2.5 for continental views.
- Highlight colors should be hex strings. Use warm colors (reds/oranges) for \
conflict/decline, cool colors (blues/greens) for growth/stability, and \
yellows for neutral change.
- Country highlight altitude: 0.0 for flat, up to 0.08 for emphasis.
- Steps should be chronologically ordered.
- Be historically plausible in your alternate scenarios.
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
    instructions=SYSTEM_PROMPT,
    output_type=AlternateTimeline,
    input_guardrails=[InputGuardrail(guardrail_function=whatif_guardrail)],
)
