from agents import InputGuardrailTripwireTriggered, Runner
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.backend.agent import historian
from src.backend.models import AlternateTimeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class TimelineRequest(BaseModel):
    question: str


@app.post("/api/timeline")
async def create_timeline(req: TimelineRequest) -> AlternateTimeline:
    try:
        result = await Runner.run(historian, req.question)
    except InputGuardrailTripwireTriggered as err:
        raise HTTPException(
            status_code=400, detail="Not a valid what-if question."
        ) from err
    output: AlternateTimeline = result.final_output  # type: ignore[assignment]
    return output
