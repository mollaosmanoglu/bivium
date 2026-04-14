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
    {"id": "brazil", "name": "Republic of Brazil", "color": "#229954"},
    {"id": "argentina", "name": "Argentine Republic", "color": "#5dade2"},
    {"id": "mexico", "name": "Republic of Mexico", "color": "#a04000"},
    {"id": "sweden", "name": "Kingdom of Sweden", "color": "#2e86c1"},
    {"id": "ethiopia", "name": "Ethiopian Empire", "color": "#196f3d"},
    {"id": "siam", "name": "Kingdom of Siam", "color": "#f1c40f"},
    {"id": "afghanistan", "name": "Emirate of Afghanistan", "color": "#784212"},
    ... (30+ total)
  ]
}
</good>
<bad>
{
  "factions": [
    {"id": "latin_am", "name": "Latin American Republics", "color": "#e67e22"}
  ]
}
</bad>

<good>
"What if Rome never fell?" → {"steps": [{"year": 117}, {"year": 476}, {"year": 800}, {"year": 1204}, {"year": 1387}]}
"What if the Ottoman Empire never fell?" → {"steps": [{"year": 1914}, {"year": 1922}, {"year": 1939}, {"year": 1955}, {"year": 1971}]}
</good>
<bad>
"What if Rome never fell?" → {"steps": [{"year": 476}, {"year": 1000}, {"year": 1500}, {"year": 1900}, {"year": 2025}]}
</bad>

<good>
"What if the Ottoman Empire never fell?"
Step 1: {"narration": "The Porte narrowly survives the Balkan Wars but emerges weakened — Kurdish unrest spreads east.", "key_events": ["Kurdish revolt in Diyarbakir crushed at heavy cost", "Britain funds Arab nationalist cells in Hejaz"]}
Step 3: {"narration": "Oil wealth floods the treasury but poisons politics — the military eyes power, the Sultan is a figurehead.", "key_events": ["Arab federalists in Baghdad threaten secession over oil royalties", "A military coup in Ankara narrowly fails"]}
Step 5: {"narration": "The empire is a bureaucratic husk — Kurdistan is autonomous, Egypt drifts toward China, and the Sultan opens a museum in the old harem.", "key_events": ["Kurdistan holds its first referendum; Constantinople can't stop it", "Egypt signs a Belt and Road port deal, sidelining Ottoman trade", "Youth protests in Ankara demand a republic; 40 arrested"]}

"What if China discovered the Americas?"
Step 1: {"narration": "Zheng He's fleet reaches Fusang but the Emperor recalls the ships — the court scholars call it a waste.", "key_events": ["Treasure Fleet makes landfall at modern-day Monterey", "Court faction led by Confucian scholars opposes further voyages"]}
Step 3: {"narration": "Chinese coastal colonies struggle — tropical disease, Aztec resistance, and a 10,000-mile supply chain.", "key_events": ["Malaria kills half the Fusang garrison in one summer", "Aztec diplomats play Ming and Inca off each other"]}
Step 5: {"narration": "The colonies have gone native — Fusang speaks a Cantonese-Nahuatl creole, ignores Beijing, and trades with Japan behind the Emperor's back.", "key_events": ["Fusang governor refuses to pay tribute for the third year running", "Japanese merchants control 60% of Pacific silver trade", "A smallpox epidemic kills 200,000 in the Mississippi colonies"]}

"What if Rome never fell?"
Step 3: {"narration": "The legions hold the Rhine but the treasury is empty — three emperors in five years, each assassinated by the next.", "key_events": ["Emperor Gaius III murdered by his own Praetorian Guard", "Plague sweeps Hispania, killing a quarter of the population", "Persian embassy demands Rome withdraw from Mesopotamia"]}
Step 5: {"narration": "Rome survives in name only — a patchwork of feuding governors who still mint coins with the Eagle but answer to no one.", "key_events": ["The governor of Britannia declares independence; Rome lacks ships to respond", "Constantinople and Rome each claim the 'true' Senate", "Barbarian foederati now command half the legions"]}
</good>
<bad>
"What if the Ottoman Empire never fell?"
Step 5: {"narration": "The Ottoman Empire mediates all global conflicts and leads humanity into a golden age of peace.", "key_events": ["Constantinople hosts the Global Peace Summit", "Ottoman Mars colony established", "The Ottoman Lira becomes the world reserve currency"]}

"What if China discovered the Americas?"
Step 5: {"narration": "A joint Ming-Aztec mission lands on the Moon. The Pacific Commonwealth rules the world in harmony.", "key_events": ["China and the Aztecs achieve world peace", "All European powers surrender to the Ming", "The Great Synthesis merges all cultures into one"]}

"What if Rome never fell?"
Step 5: {"narration": "The Roman Space Agency launches humanity's first interstellar probe. All nations live under the Pax Romana.", "key_events": ["Roman fusion reactors power the entire planet", "Global digital citizenship granted to every human", "The Senate votes to colonize Alpha Centauri"]}
</bad>

<good>
Step (1969):
{"faction_id": "nigerian", "countries": ["NGA", "GHA", "SLE", "GMB"]}
{"faction_id": "saudi", "countries": ["SAU", "OMN", "ARE", "QAT"]}
{"faction_id": "argentinian", "countries": ["ARG", "URY", "PRY"]}
{"faction_id": "indonesian", "countries": ["IDN", "TLS", "BRN"]}
{"faction_id": "kenyan", "countries": ["KEN", "UGA", "TZA"]}
{"faction_id": "congolese", "countries": ["COD", "COG", "CAF"]}
</good>
<bad>
Step (1969):
{"faction_id": "unaligned", "countries": ["NGA", "GHA", "SLE", "SYR", "SAU", "PHL", "ARG", "CHL", "PER", "IDN", "FJI", "KEN", "TZA", "COD", "COG"]}
{"faction_id": "western", "countries": ["USA", "CAN", "GBR", "FRA", "DEU", "ITA", "ESP", "PRT", "NLD", "BEL", "NOR", "SWE", "DNK", "AUS", "NZL", "JPN", "KOR"]}
{"faction_id": "african_union", "countries": ["NGA", "GHA", "KEN", "TZA", "ETH", "ZAF", "COD", "CMR", "SEN", "MLI", "NER", "TCD", "CAF", "AGO", "MOZ"]}
</bad>
</examples>

<constraints>
- Generate exactly 5 steps. No fewer, no more.
- Every country in exactly one entry per step. No duplicates, no gaps.
- Each entry is a sovereign entity (empire, kingdom, republic) — not a bloc or alliance.
- When an entity evolves (Ottoman Empire -> Ottoman Republic), keep the SAME id. \
Update the leader and description — don't create a new entity.
- Each step should have MORE active entries than the previous.
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
        max_output_tokens=65536,
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
