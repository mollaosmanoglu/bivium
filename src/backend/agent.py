from __future__ import annotations

from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from src.backend.geo import all_iso_codes
from src.backend.models import AlternateTimeline

MODEL = "gemini-3-flash-preview"

client = genai.Client()

SYSTEM_PROMPT = """\
<role>
You are a historian and geopolitics expert. Given a "what if" question, \
generate a cinematic alternate-history timeline as a full-world political \
map on a 3D globe — like EU4 or Hearts of Iron.
</role>

<goal>
Paint the ENTIRE world in every step. No empty land. Every country belongs \
to a faction. The globe must be richly colored with 12+ distinct factions.
</goal>

<examples>
<good>
"What if the Ottoman Empire never fell?" (1914):
  13 factions: Ottoman, British, French, German, Russian, Austro-Hungarian, \
  American, Japanese, Chinese, Italian, Persian, Latin American, Unaligned.
  Each sub-region has max 15 countries with a historical name.
  "Unaligned" is small — only Nordic neutrals, Iberia, and a few others.
</good>

<bad>
Only 4 factions: Ottoman, British, Russian, Unaligned.
  "Unaligned" has 128 countries in one giant blob called "Global Independents".
  This is lazy — France, Germany, Japan, USA, etc. all deserve their own faction.
</bad>

<bad>
A sub-region with 60 countries called "African and Asian Independents".
  Never put more than 20 countries in a single sub-region. Split by geography.
</bad>
</examples>

<constraints>
- At least 12 factions per timeline. Unaligned should be the smallest faction.
- Every country in exactly one faction per step. No duplicates, no gaps.
- Sub-regions: max 20 countries each. Core homeland listed FIRST.
- Include a faction with id "unaligned" and color "#7f8c8d" for true neutrals.
</constraints>
"""


def _build_instructions() -> str:
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


def _get_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=_build_instructions(),
        response_mime_type="application/json",
        response_schema=AlternateTimeline,
    )


async def generate_timeline(question: str) -> AlternateTimeline:
    """Non-streaming: generate a full timeline."""
    response = await client.aio.models.generate_content(  # pyright: ignore[reportUnknownMemberType]
        model=MODEL,
        contents=question,
        config=_get_config(),
    )
    text: str = response.text or ""
    return AlternateTimeline.model_validate_json(text)


async def stream_timeline_chunks(question: str) -> AsyncGenerator[str, None]:
    """Streaming: yield partial JSON text chunks."""
    stream = await client.aio.models.generate_content_stream(  # pyright: ignore[reportUnknownMemberType]
        model=MODEL,
        contents=question,
        config=_get_config(),
    )
    async for chunk in stream:
        text: str | None = chunk.text
        if text:
            yield text
