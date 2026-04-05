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
<example>
Question: "What if the Ottoman Empire never fell?"
Step 1 (1683):
  camera: lat=39, lng=32, altitude=2.0
  narration: "After lifting the Siege of Vienna, the Ottoman Empire consolidates its grip on Southeast Europe and the Levant."
  factions:
    - Ottoman Empire | #c0392b | Sultan Mehmed V | "A sprawling multi-ethnic empire controlling three continents"
      Rumelia: GRC, BGR, SRB, BIH, ALB, MKD, MNE, KOS, HRV
      Anatolia: TUR, CYP
      Mashriq: SYR, IRQ, JOR, LBN, ISR, PSE
      Egypt: EGY, LBY, TUN
      Hijaz: SAU, YEM, OMN
    - Habsburg Empire | #2980b9 | Emperor Leopold I | "Catholic bulwark of Central Europe"
      Austria: AUT, HUN, CZE, SVK, SVN
      Low Countries: BEL, NLD, LUX
    - Kingdom of France | #8e44ad | Louis XIV | "The Sun King's domain at its zenith"
      Metropolitan France: FRA, MCO
      Colonies: SEN, MLI
    - Russian Tsardom | #27ae60 | Peter the Great | "An expanding northern giant"
      Muscovy: RUS, BLR, UKR
      Siberia: KAZ, MNG
    - Qing Dynasty | #e67e22 | Kangxi Emperor | "Mandate of Heaven over East Asia"
      China Proper: CHN, TWN
      Tributaries: KOR, VNM, LAO, KHM, MMR
    - Mughal Empire | #f39c12 | Aurangzeb | "Islamic empire spanning the subcontinent"
      Hindustan: IND, PAK, BGD, LKA, NPL
    - Rest of World | #7f8c8d | — | "Unaligned or colonial territories"
      Americas: USA, CAN, MEX, BRA, ARG, ...remaining countries
</example>

<example>
Question: "What if Rome never fell?"
Step 1 (476):
  factions:
    - Roman Empire | #c0392b | Emperor Julius Nepos | "The eternal empire, unbroken"
      Italia: ITA, MLT, SMR, VAT
      Gallia: FRA, BEL, LUX, CHE
      Hispania: ESP, PRT
      Britannia: GBR, IRL
      Africa: TUN, LBY, DZA, MAR, EGY
      Oriens: TUR, SYR, LBN, ISR, JOR, IRQ, CYP, GRC
    - Sassanid Empire | #2980b9 | Peroz I | "Zoroastrian rival to Rome's east"
      Persia: IRN, AFG
      Mesopotamia: KWT, BHR, QAT, ARE, OMN
    ... (fill every country into some faction)
</example>
</examples>

<constraints>
- Every modern country must appear in exactly one faction per step. No gaps.
- Include a catch-all faction (e.g. "Unaligned Territories") for countries \
not part of a major power. Use #7f8c8d (gray) for these.
- Use real ISO 3166-1 alpha-3 codes (TUR, GBR, USA, DEU, FRA, RUS, CHN, etc.)
- Split factions into 2-5 sub-regions with historical names.
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
    model="gpt-5.4",
    instructions=SYSTEM_PROMPT,
    output_type=AlternateTimeline,
    input_guardrails=[InputGuardrail(guardrail_function=whatif_guardrail)],
)
