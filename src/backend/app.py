from dotenv import load_dotenv

load_dotenv(override=True)

from agents import InputGuardrailTripwireTriggered, Runner  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from src.backend.agent import historian  # noqa: E402
from src.backend.models import AlternateTimeline  # noqa: E402

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
