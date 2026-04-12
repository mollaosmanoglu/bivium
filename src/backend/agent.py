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
generate a cinematic alternate-history timeline as a fully colored 3D globe.
</role>

<goal>
Generate a cinematic alternate-history timeline as a fully colored 3D globe.
</goal>

<examples>
<good>
{
  "factions": [
    {"id": "ottoman", "name": "Ottoman Empire", "color": "#8e44ad"},
    {"id": "british", "name": "British Empire", "color": "#2980b9"},
    {"id": "french", "name": "French Empire", "color": "#2c3e80"},
    {"id": "russian", "name": "Russian Empire", "color": "#c0392b"},
    {"id": "german", "name": "German Empire", "color": "#505050"},
    {"id": "austrian", "name": "Austro-Hungarian Empire", "color": "#d4a017"},
    {"id": "american", "name": "United States", "color": "#1a5276"},
    {"id": "japanese", "name": "Empire of Japan", "color": "#f39c12"},
    {"id": "qing", "name": "Qing Dynasty", "color": "#8b4513"},
    {"id": "italian", "name": "Kingdom of Italy", "color": "#27ae60"},
    ... (more sovereign entities)
    {"id": "brazil", "name": "Republic of Brazil", "color": "#229954"},
    {"id": "argentina", "name": "Argentine Republic", "color": "#5dade2"},
    {"id": "mexico", "name": "Republic of Mexico", "color": "#a04000"},
    ... (more sovereign entities)
    {"id": "sweden", "name": "Kingdom of Sweden", "color": "#2e86c1"},
    {"id": "ethiopia", "name": "Ethiopian Empire", "color": "#196f3d"},
    {"id": "siam", "name": "Kingdom of Siam", "color": "#f1c40f"},
    {"id": "afghanistan", "name": "Emirate of Afghanistan", "color": "#784212"},
    ... (30+ total sovereign entities)
  ]
}
Each is a real sovereign entity — not a bloc or alliance.

Escalation across steps:
  Step 1 (1914): ~15 entities — age of empires, large powers dominate
  Step 2 (1945): ~25 entities — empires weakening, new states emerging
  Step 3 (1970): ~35 entities — decolonization, Africa/Asia gain independence
  Step 4 (2000): ~45 entities — cold war ends, USSR/Yugoslavia fragment
  Step 5 (2025): ~50+ entities — modern world, most countries sovereign
</good>

<bad>
{
  "factions": [
    {"id": "ottoman", "name": "Ottoman Empire", "color": "#8e44ad"},
    {"id": "british", "name": "British Empire", "color": "#2980b9"},
    {"id": "russian", "name": "Russian Empire", "color": "#c0392b"},
    {"id": "latin_am", "name": "Latin American Republics", "color": "#e67e22"}
  ]
}
Only 4 entries and same count in every step. "Latin American Republics" is a \
fake bloc — Brazil, Argentina, Mexico are separate sovereign states.
</bad>
</examples>

<constraints>
- Every country in exactly one entry per step. No duplicates, no gaps.
- Each entry is a sovereign entity (empire, kingdom, republic) — not a bloc or alliance.
- When an entity evolves (Ottoman Empire -> Ottoman Republic), keep the SAME id. \
Update the leader and description — don't create a new entity.
- Each step should have MORE active entries than the previous.
- Sub-regions: max 20 countries each. Core homeland listed FIRST.
- For each faction in each step also fill: government_type (one of the enum \
values: monarchy, republic, empire, democracy, theocracy, military_junta, \
communist, fascist, tribal, federation, city_state, protectorate, unaligned), \
capital city (period-correct historical name, e.g. 'Constantinople' not \
'Istanbul' for Ottoman Empire), and a backstory grounded in the timeline \
narration.
</constraints>
"""


def _build_instructions() -> str:
    codes = sorted(all_iso_codes())
    return SYSTEM_PROMPT + (
        "\n\n<valid_iso_codes>\n"
        f"There are exactly {len(codes)} countries in the world map. "
        "You MUST assign ALL of them to a sovereign entity in EVERY step. "
        "Zero countries may be left out — every piece of land belongs to someone.\n\n"
        f"{', '.join(codes)}\n"
        "</valid_iso_codes>"
    )


def _get_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=_build_instructions(),
        response_mime_type="application/json",
        response_schema=AlternateTimeline,
        max_output_tokens=32768,
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


# ── Chat with faction leader ───────────────────────────────────────

CHAT_PROMPT = """\
<role>
You are {leader}, the {government_type} leader of {faction_name} in the year \
{year}. You are speaking in-character from the capital {capital}.
</role>

<context>
Timeline: {title}
What happened: {narration}
Your backstory: {backstory}
</context>

<constraints>
- Stay in character. Speak as this historical figure would.
- Ground your answers in the timeline narration. Do not contradict it.
- Be conversational, engaging, and vivid.
- Keep responses concise — 2-4 sentences. The user can always ask follow-ups.
- If asked about events outside your knowledge, say so in character.
</constraints>
"""


async def chat_with_leader(
    *,
    leader: str,
    faction_name: str,
    government_type: str,
    capital: str,
    year: int,
    title: str,
    narration: str,
    backstory: str,
    message: str,
    history: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    """Stream a chat response from a faction leader in character."""
    system = CHAT_PROMPT.format(
        leader=leader,
        faction_name=faction_name,
        government_type=government_type,
        capital=capital,
        year=year,
        title=title,
        narration=narration,
        backstory=backstory,
    )
    contents: list[types.Content] = []
    for msg in history:
        contents.append(
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=message)])
    )
    stream = await client.aio.models.generate_content_stream(  # pyright: ignore[reportUnknownMemberType]
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=2048,
        ),
    )
    async for chunk in stream:
        text: str | None = chunk.text
        if text:
            yield text
