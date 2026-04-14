<p align="center">
  <img src="docs/logo.png" alt="Bivium logo" width="200"/>
</p>

# Bivium

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Stars](https://img.shields.io/github/stars/mollaosmanoglu/bivium)

Open-source alternate history engine. Multi-agent AI simulations of geopolitical scenarios on an interactive 3D globe.

<p align="center">
  <img src="docs/demo.gif" alt="Alternate history simulation" width="800"/>
</p>

## Visual Overview

<p align="center">
  <img src="docs/flow.png" alt="System architecture" width="700"/>
</p> 


| Layer    | Tech                                                                     |
| -------- | ------------------------------------------------------------------------ |
| AI       | OpenAI Agents SDK — structured output, input guardrails, Pydantic models |
| Backend  | FastAPI, Shapely (polygon merging), Natural Earth GeoJSON                |
| Frontend | Next.js, react-globe.gl, shadcn/ui, Motion                               |
| Dev      | uv, Ruff, Pyright, Biome                                                 |


## Quickstart

```bash
# Backend
cp .env.example .env  # add your OPENAI_API_KEY
uv sync
uv run uvicorn src.backend.app:app --reload --port 8001

# Frontend
cd src/frontend
bun install
bun dev
```

Open [localhost:3000](http://localhost:3000), type a question, and watch.

## Project structure

```
src/
  backend/
    agent.py       # Historian + guardrail agents (OpenAI Agents SDK)
    app.py         # FastAPI endpoint, polygon merging pipeline
    models.py      # Pydantic models (input from AI, output with GeoJSON)
    geo.py         # Country polygon lookup + Shapely merge
    data/          # Natural Earth provinces GeoJSON (10m)
  frontend/
    src/
      app/         # Next.js app router
      components/
        globe.tsx  # 3D globe viewer with animated playback
        ui/        # shadcn components
    public/data/   # Natural Earth countries GeoJSON (110m)
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  Frontend (Next.js)                         │
│  ┌─────────┐  ┌──────────────────────────┐  │
│  │ Input   │  │ Globe Viewer             │  │
│  │ Card    │──│ • react-globe.gl         │  │
│  │         │  │ • Faction polygons       │  │
│  └─────────┘  │ • Camera animation       │  │
│               │ • Year/narration overlay  │  │
│               └──────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │ POST /api/timeline
┌──────────────────▼──────────────────────────┐
│  Backend (FastAPI)                           │
│  ┌────────────┐  ┌────────────────────────┐ │
│  │ Guardrail  │  │ Historian Agent        │ │
│  │ (nano)     │──│ (gpt-5.4)             │ │
│  │ validates  │  │ generates timeline     │ │
│  └────────────┘  └───────────┬────────────┘ │
│                              │              │
│  ┌───────────────────────────▼────────────┐ │
│  │ Geo Pipeline                           │ │
│  │ ISO codes → Shapely merge → GeoJSON    │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## License

MIT