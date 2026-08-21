import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .data import (
    MODEL_LIMITATIONS,
    comparison_payload,
    fingerprint_payload,
    neighbours_payload,
    team_names,
)
from .explanations import generate_explanation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(
    title="Tactical Style Fingerprint API",
    version="1.0.0",
    description=(
        "Serves validated Premier League 2015/16 tactical fingerprints, "
        "similarities, and grounded AI explanations."
    ),
)

allowed_origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    os.getenv("FRONTEND_ORIGIN", "").strip(),
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origin for origin in allowed_origins if origin),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ExplanationRequest(BaseModel):
    team_a: str
    team_b: str


def not_found(team: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Unknown team: {team}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "teams_loaded": len(team_names())}


@app.get("/teams")
def teams() -> dict:
    return {
        "season": "Premier League 2015/16",
        "teams": team_names(),
        "model": "Five equal-weight population z-scores with Euclidean distance",
        "limitations": MODEL_LIMITATIONS,
    }


@app.get("/teams/{team}/fingerprint")
def fingerprint(team: str) -> dict:
    try:
        return fingerprint_payload(team)
    except KeyError:
        raise not_found(team) from None


@app.get("/teams/{team}/neighbours")
def neighbours(team: str, limit: int = Query(default=5, ge=1, le=19)) -> dict:
    try:
        return neighbours_payload(team, limit)
    except KeyError:
        raise not_found(team) from None


@app.get("/compare")
def compare(team_a: str, team_b: str) -> dict:
    try:
        return comparison_payload(team_a, team_b)
    except KeyError as error:
        raise not_found(str(error.args[0])) from None


@app.post("/explain")
async def explain(request: ExplanationRequest) -> dict:
    if request.team_a == request.team_b:
        raise HTTPException(status_code=400, detail="Choose two different teams")
    try:
        comparison = comparison_payload(request.team_a, request.team_b)
    except KeyError as error:
        raise not_found(str(error.args[0])) from None

    try:
        explanation, model = await generate_explanation(comparison)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Featherless timed out. The tactical comparison still works; try again.",
        ) from None
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        raise HTTPException(
            status_code=502,
            detail=(
                f"Featherless could not generate an explanation (provider status "
                f"{status}). The rest of the comparison remains available."
            ),
        ) from None
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach Featherless. The tactical comparison still "
                "works; check the backend connection and try again."
            ),
        ) from None

    return {
        "team_a": request.team_a,
        "team_b": request.team_b,
        "model": model,
        "explanation": explanation,
        "grounding_note": (
            "Generated from the calculated five-feature comparison and supplied "
            "metric limitations, not from unrestricted club-name knowledge."
        ),
    }
