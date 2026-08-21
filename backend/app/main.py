import os
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
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


def positive_int_environment(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


EXPLAIN_RATE_LIMIT_REQUESTS = positive_int_environment(
    "EXPLAIN_RATE_LIMIT_REQUESTS", 5
)
EXPLAIN_RATE_LIMIT_WINDOW_SECONDS = positive_int_environment(
    "EXPLAIN_RATE_LIMIT_WINDOW_SECONDS", 600
)
explain_attempts: defaultdict[str, deque[float]] = defaultdict(deque)
explain_attempts_lock = Lock()


def explanation_client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else "unknown"


def check_explanation_rate_limit(client_id: str) -> int | None:
    now = time.monotonic()
    cutoff = now - EXPLAIN_RATE_LIMIT_WINDOW_SECONDS
    with explain_attempts_lock:
        attempts = explain_attempts[client_id]
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= EXPLAIN_RATE_LIMIT_REQUESTS:
            return max(1, int(EXPLAIN_RATE_LIMIT_WINDOW_SECONDS - (now - attempts[0])))
        attempts.append(now)
    return None


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
async def explain(payload: ExplanationRequest, request: Request) -> dict:
    retry_after = check_explanation_rate_limit(explanation_client_id(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many explanation requests. The tactical data remains "
                "available; wait before requesting another AI explanation."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    if payload.team_a == payload.team_b:
        raise HTTPException(status_code=400, detail="Choose two different teams")
    try:
        comparison = comparison_payload(payload.team_a, payload.team_b)
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
        "team_a": payload.team_a,
        "team_b": payload.team_b,
        "model": model,
        "explanation": explanation,
        "grounding_note": (
            "Generated from the calculated five-feature comparison and supplied "
            "metric limitations, not from unrestricted club-name knowledge."
        ),
    }
