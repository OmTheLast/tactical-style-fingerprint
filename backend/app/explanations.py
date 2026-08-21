import json
import os

import httpx

from .data import FEATURES, MODEL_LIMITATIONS


FEATHERLESS_CHAT_URL = "https://api.featherless.ai/v1/chat/completions"

SYSTEM_PROMPT = """You explain a football tactical comparison using only the structured evidence supplied by the application.

Rules:
- Do not invent or use facts about players, managers, formations, matches, results, trophies, eras, or club history.
- Do not claim that either team is better.
- Do not interpret distance as a probability, percentage, or percentage of tactical identity.
- Clearly distinguish measured evidence from cautious tactical interpretation.
- Explain the strongest similarities, strongest differences, and important uncertainty.
- Mention that nearest does not necessarily mean very close when the distance or feature gaps are substantial.
- Use concise plain language suitable for a football fan. Aim for 3 to 5 short paragraphs.
"""


def explanation_evidence(comparison: dict) -> dict:
    definitions = {
        feature["label"]: {
            "definition": feature["definition"],
            "high_value_means": feature["high_meaning"],
            "limitation": feature["limitation"],
        }
        for feature in FEATURES
    }
    return {
        "focal_team": comparison["team_a"]["team"],
        "comparison_team": comparison["team_b"]["team"],
        "euclidean_tactical_distance": comparison["euclidean_distance"],
        "distance_interpretation": comparison["distance_note"],
        "focal_team_features": comparison["team_a"]["features"],
        "comparison_team_features": comparison["team_b"]["features"],
        "signed_feature_differences": comparison["feature_differences"],
        "metric_definitions": definitions,
        "known_model_limitations": MODEL_LIMITATIONS,
    }


async def generate_explanation(comparison: dict) -> tuple[str, str]:
    api_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    model = os.getenv("FEATHERLESS_MODEL", "").strip()
    if not api_key or not model:
        raise RuntimeError(
            "Featherless is not configured. Set FEATHERLESS_API_KEY and "
            "FEATHERLESS_MODEL in your local environment."
        )

    base_url = os.getenv("FEATHERLESS_BASE_URL", "").strip()
    chat_url = (
        f"{base_url.rstrip('/')}/chat/completions"
        if base_url
        else FEATHERLESS_CHAT_URL
    )
    evidence = explanation_evidence(comparison)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("APP_PUBLIC_URL", "http://localhost:3000"),
        "X-Title": "Tactical Style Fingerprint",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Explain this matchup using only the following JSON data:\n"
                    + json.dumps(evidence, indent=2)
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 700,
    }

    async with httpx.AsyncClient(timeout=35.0) as client:
        response = await client.post(chat_url, headers=headers, json=body)
        response.raise_for_status()
        payload = response.json()

    try:
        explanation = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise RuntimeError("Featherless returned an unexpected response shape") from error
    if not explanation:
        raise RuntimeError("Featherless returned an empty explanation")
    return explanation, model
