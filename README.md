# Bivium

Type a "what if" question, get a cinematic 3D globe animation showing the alternate timeline.

**Example**: *"What if the Ottoman Empire never fell?"* → animated globe with countries lighting up, text narration stepping through the timeline.

## How it works

1. User types a question
2. OpenAI Agent returns a structured timeline (year, narration, camera position, country highlights)
3. Frontend animates the globe step-by-step with text overlay

## Via negativa

What we deliberately removed to keep the product sharp:

- ~~Voice/TTS~~ — text narration only. Voice is 40x more expensive and adds sync complexity. Add later if the core works.
- ~~Comparison view~~ — no "alternate vs actual" split-screen. One timeline, one globe.
- ~~Sharing/persistence~~ — ephemeral results. No database, no URLs, no accounts.
- ~~Globe interactivity~~ — cinematic only. No click, no drag, no zoom.
- ~~Border morphing~~ — color existing country polygons by ISO code. No custom geometry.
- ~~Multiple globes~~ — one globe, one animation.

## Stack

- **Backend**: FastAPI + OpenAI Agents SDK (structured output + guardrails)
- **Frontend**: Next.js + react-globe.gl + shadcn + Motion
- **Data**: Natural Earth GeoJSON (country polygons)
