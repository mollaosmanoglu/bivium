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

from src.backend.geo import all_iso_codes
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
10+ factions covering the ENTIRE world — no lazy gray blobs:

Top-level factions:
  id="ottoman", name="Ottoman Empire", color="#8e44ad"
  id="russian", name="Russian Empire", color="#c0392b"
  id="british", name="British Empire", color="#2980b9"
  id="french", name="French Empire", color="#2c3e80"
  id="german", name="German Empire", color="#505050"
  id="austrian", name="Austro-Hungarian Empire", color="#d4a017"
  id="american", name="United States", color="#1a5276"
  id="japanese", name="Empire of Japan", color="#f39c12"
  id="chinese", name="Qing Dynasty", color="#8b4513"
  id="italian", name="Kingdom of Italy", color="#27ae60"
  id="persian", name="Qajar Persia", color="#16a085"
  id="latin_am", name="Latin American Republics", color="#e67e22"
  id="unaligned", name="Independent States", color="#7f8c8d"

Step (year: 1914), faction_states:
  faction_id="british":
    "The Home Islands" (GBR, IRL)
    "Raj of Hindustan" (IND, PAK, BGD, LKA, NPL, BTN)
    "Dominion of Canada" (CAN)
    "Australasian Dominions" (AUS, NZL)
    "Southern African Holdings" (ZAF, NAM, BWA, ZWE, ZMB, MWI)
    "West African Colonies" (NGA, GHA, SLE, GMB)
    "East African Protectorates" (KEN, TZA, UGA)
    "Egyptian Protectorate" (EGY, SDN)
  faction_id="french":
    "Metropolitan France" (FRA, BEL, LUX)
    "Afrique Occidentale" (SEN, MLI, BFA, CIV, GIN, NER, TCD, MRT)
    "Afrique Equatoriale" (CMR, GAB, COG, CAF)
    "Maghreb Colonies" (DZA, TUN, MAR)
    "Indochine" (VNM, LAO, KHM)
    "Madagascar" (MDG)
  faction_id="german":
    "Kaiserreich Heartland" (DEU)
    "Kamerun und Togo" (TGO, BEN, GNQ)
    "Deutsch-Ostafrika" (BDI, RWA)
    "Südwestafrika" (AGO, MOZ)
  faction_id="ottoman":
    "Eyalet of Rumelia" (GRC, BGR, ALB, MKD, MNE)
    "Anatolia and the Straits" (TUR, CYP)
    "Vilayet of the Levant" (SYR, LBN, JOR, PSE, ISR)
    "Vilayet of Basra" (IRQ, KWT)
    "Vilayet of Hijaz" (SAU, YEM, OMN, ARE, QAT, BHR)
  faction_id="russian":
    "European Russia" (RUS, BLR, UKR, MDA)
    "Baltic Governorates" (LTU, LVA, EST, FIN)
    "Caucasus Viceroyalty" (GEO, ARM, AZE)
    "Turkestan" (KAZ, UZB, TKM, KGZ, TJK)
    "Siberia and Far East" (MNG)
  faction_id="austrian":
    "Habsburg Crownlands" (AUT, HUN, CZE, SVK, HRV, SVN, BIH, SRB)
    "Transylvania and Galicia" (ROU, POL)
  faction_id="japanese":
    "Home Islands" (JPN)
    "Korean Protectorate" (PRK, KOR)
    "Formosa" (TWN)
  faction_id="chinese":
    "Middle Kingdom" (CHN)
  faction_id="american":
    "Continental United States" (USA)
    "Caribbean and Pacific" (CUB, DOM, HTI, JAM, TTO, PAN)
    "Philippine Islands" (PHL)
  faction_id="persian":
    "Qajar Domains" (IRN, AFG)
  faction_id="italian":
    "Italian Peninsula" (ITA)
    "Libyan Colony" (LBY)
    "Horn of Africa" (ERI, SOM, DJI, ETH)
  faction_id="latin_am":
    "Southern Cone" (ARG, CHL, URY, PRY)
    "Andean Republics" (PER, BOL, ECU, COL, VEN)
    "Brazil" (BRA)
    "Central America" (MEX, GTM, SLV, HND, NIC, CRI, BLZ)
    "Guianas" (GUY, SUR)
  faction_id="unaligned":
    "Nordic Neutrals" (DNK, NOR, SWE, ISL)
    "Iberian Kingdoms" (ESP, PRT)
    "Low Countries" (NLD, CHE)
    "Southeast Asian Kingdoms" (THA, MMR)
    "Pacific Islands" (IDN, MYS, BRN, TLS, PNG, FJI, SGP)
    "Remaining Africa" (LBR, COD, GNB, SWZ, LSO)
</good_example>

<bad_example>
Only 3 factions + a massive "Unaligned" blob:
  Ottoman Empire (20 countries)
  British Empire (15 countries)
  Russian Empire (10 countries)
  Unaligned Territories (128 countries in 2 sub-regions!)
This is lazy. France, Germany, Austria-Hungary, Japan, USA, Italy, Persia, \
China, and Latin America all deserve their own factions. Aim for 8-15 factions \
so the entire globe is richly colored.
</bad_example>

<bad_example>
Vague sub-region names:
  "Global Independents" (USA, CAN, MEX, BRA, ARG, CHN, JPN, ...)
  "African and Asian Independents" (60+ countries)
These are not real historical groupings. Use period-accurate names.
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


def _dynamic_instructions(ctx: RunContextWrapper[None], agent: Agent[None]) -> str:
    codes = sorted(all_iso_codes())
    return SYSTEM_PROMPT + (
        "\n\n<valid_iso_codes>\n"
        f"There are exactly {len(codes)} countries in the world map. "
        "You MUST assign ALL of them to a faction in EVERY step. "
        "If a country is not part of a major power, put it in the "
        '"unaligned" faction. Zero countries may be left out — the globe '
        "must be fully colored with no dark/empty areas.\n\n"
        f"{', '.join(codes)}\n"
        "</valid_iso_codes>"
    )


historian: Agent[None] = Agent(
    name="Historian",
    model="gpt-5.4",
    instructions=_dynamic_instructions,
    output_type=AlternateTimeline,
    # input_guardrails=[InputGuardrail(guardrail_function=whatif_guardrail)],
)
