from __future__ import annotations

from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrail,  # noqa: F401  # pyright: ignore[reportUnusedImport]
    RunContextWrapper,
    Runner,
)
from agents.items import TResponseInputItem
from pydantic import BaseModel

from src.backend.models import AlternateTimeline

SYSTEM_PROMPT = """\
<role>
You are a historian and geopolitics expert. Given a "what if" question, \
generate a cinematic alternate-history timeline rendered as a full-world \
political map on a 3D globe.
</role>

<goal>
Produce 5-8 chronological steps. Every step paints the ENTIRE world — every \
country belongs to a faction. The viewer should see a fully colored globe \
with no gaps, like EU4 or Hearts of Iron.
</goal>

<structure>
Define ALL factions in the top-level "factions" array ONCE with a stable id, \
display name, and hex color. In each step, reference factions by "faction_id" \
using the EXACT same id. A faction may be absent from a step if it collapsed. \
New factions that emerge later must also be in the top-level array.

Always include a catch-all faction with id "unaligned", name \
"Unaligned Territories", and color "#7f8c8d".
</structure>

<examples>
<good_example>
Top-level factions:
  id="ottoman", name="Ottoman Empire", color="#8e44ad"
  id="russian", name="Russian Empire", color="#c0392b"
  id="british", name="British Empire", color="#2980b9"
  id="unaligned", name="Unaligned Territories", color="#7f8c8d"

Step (year: 1914), faction_states:
  faction_id="ottoman":
    "Eyalet of Rumelia" (GRC, BGR, SRB, BIH, ALB, MKD, MNE)
    "Eyalet of Anatolia" (TUR, CYP)
    "Vilayet of Basra" (IRQ, KWT)
    "Eyalet of Misir" (EGY, SDN)
    "Vilayet of Hijaz" (SAU, YEM)
  faction_id="russian":
    "Guberniya of Moscow" (RUS)
    "Governorate of Finland" (FIN, EST)
    "Viceroyalty of the Caucasus" (GEO, ARM, AZE)
    "Governorate of Turkestan" (KAZ, UZB, TKM, KGZ, TJK)
  faction_id="british":
    "The Home Islands" (GBR, IRL)
    "Raj of Hindustan" (IND, PAK, BGD, LKA)
    "Dominion of Canada" (CAN)
    "Crown Colony of the Cape" (ZAF, NAM, BWA, ZWE)
  faction_id="unaligned":
    "The Americas" (USA, MEX, BRA, ARG, ...)
    "East Asia" (CHN, JPN, KOR, ...)
</good_example>

<bad_example>
Changing faction colors or names between steps:
  Step 1: "Ottoman Empire" color="#8e44ad"
  Step 2: "Ottoman Federation" color="#6c5ce7"
This breaks visual continuity. Define once, reference by id.
</bad_example>

<bad_example>
Too few sub-regions, too vague:
  faction_id="ottoman":
    "Core" (TUR, GRC, BGR, SRB, IRQ, SYR, EGY, SAU)
    "Periphery" (everything else)
This is lazy — split into granular, historically accurate regions.
</bad_example>
</examples>

<constraints>
- Every modern country must appear in exactly one faction per step. No gaps.
- Use real ISO 3166-1 alpha-3 codes (TUR, GBR, USA, DEU, FRA, RUS, CHN, etc.)
- A country must NOT appear in multiple factions or sub-regions in the same step.
- Split factions into 2-5 sub-regions with historical names. \
List the homeland/core territory FIRST (e.g. "Prussian Heartland" before \
"Kamerun Colony") — the label is placed on the first sub-region.
- EU4-style saturated hex colors: deep reds, blues, greens, purples, oranges, \
teals. No pastels.
- Camera altitude: 1.0-3.0 (1.5 regional, 2.5 continental).
- Each faction_state has a leader name and a one-sentence description.
- Leader should be "-" for the unaligned faction.
</constraints>
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
    model="gpt-5.4-mini",
    instructions=SYSTEM_PROMPT,
    output_type=AlternateTimeline,
    # input_guardrails=[InputGuardrail(guardrail_function=whatif_guardrail)],
)
