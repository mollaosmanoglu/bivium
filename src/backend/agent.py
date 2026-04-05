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

<examples>
<good_example>
Granular, period-accurate sub-regions (4-5 per faction):
  Ottoman Empire:
    "Eyalet of Rumelia" (GRC, BGR, SRB, BIH, ALB, MKD, MNE)
    "Eyalet of Anatolia" (TUR, CYP)
    "Vilayet of Basra" (IRQ, KWT)
    "Eyalet of Misir" (EGY, SDN)
    "Vilayet of Hijaz" (SAU, YEM)
  Russian Empire:
    "Guberniya of Moscow" (RUS)
    "Governorate of Finland" (FIN, EST)
    "Viceroyalty of the Caucasus" (GEO, ARM, AZE)
    "Governorate of Turkestan" (KAZ, UZB, TKM, KGZ, TJK)
    "Khanate of Khiva (vassal)" (MNG)
  British Empire:
    "The Home Islands" (GBR, IRL)
    "Raj of Hindustan" (IND, PAK, BGD, LKA)
    "Dominion of Canada" (CAN)
    "Crown Colony of the Cape" (ZAF, NAM, BWA, ZWE)
    "Protectorate of Egypt" (EGY, SDN)
</good_example>

<bad_example>
Too few sub-regions, too vague:
  Ottoman Empire with only 2 sub-regions:
    "Core" (TUR, GRC, BGR, SRB, IRQ, SYR, EGY, SAU)
    "Periphery" (everything else)
This is lazy — split into 4-5 historically accurate regions.
</bad_example>

<bad_example>
Generic geography names with no historical flavor:
  "Middle East", "Southeast Asia", "Central Europe", "South America", \
  "Western Africa", "East Asia", "Northern Europe", "Russian Core"
</bad_example>

<bad_example>
Modern names on historical empires:
  "Turkey", "Iraq Region", "French Zone", "China Proper", "India"
These break the historical illusion.
</bad_example>
</examples>

<constraints>
- Every modern country must appear in exactly one faction per step. No gaps.
- Include a catch-all faction (e.g. "Unaligned Territories") for countries \
not part of a major power. Use #7f8c8d (gray) for these.
- Use real ISO 3166-1 alpha-3 codes (TUR, GBR, USA, DEU, FRA, RUS, CHN, etc.)
- Split factions into 2-5 sub-regions with historical names. \
List the homeland/core territory FIRST (e.g. "Prussian Heartland" before \
"Kamerun Colony") — the label is placed on the first sub-region.
- EU4-style saturated hex colors: deep reds, blues, greens, purples, oranges, \
teals. No pastels.
- Camera altitude: 1.0-3.0 (1.5 regional, 2.5 continental).
- Each faction has a leader name and a one-sentence description.
- Leader should be "-" for catch-all/unaligned factions.
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
    input_guardrails=[InputGuardrail(guardrail_function=whatif_guardrail)],
)
