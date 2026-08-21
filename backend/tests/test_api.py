from fastapi.testclient import TestClient

from backend.app import main
from backend.app.data import comparison_payload
from backend.app.explanations import SYSTEM_PROMPT, explanation_evidence


client = TestClient(main.app)


def setup_function() -> None:
    main.explain_attempts.clear()


def test_health_and_teams() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "teams_loaded": 20}

    response = client.get("/teams")
    assert response.status_code == 200
    assert len(response.json()["teams"]) == 20


def test_fingerprint_has_raw_z_and_display_values() -> None:
    response = client.get("/teams/Liverpool/fingerprint")
    assert response.status_code == 200
    payload = response.json()
    assert payload["team"] == "Liverpool"
    assert len(payload["features"]) == 5
    for feature in payload["features"]:
        assert isinstance(feature["raw_value"], float)
        assert isinstance(feature["z_score"], float)
        assert 0 <= feature["display_value"] <= 100


def test_neighbours_and_comparison_match_validated_distance() -> None:
    neighbours = client.get("/teams/Liverpool/neighbours").json()["neighbours"]
    assert len(neighbours) == 5
    assert neighbours[0]["team"] == "Tottenham Hotspur"
    assert abs(neighbours[0]["euclidean_distance"] - 0.619924) < 1e-6

    comparison = client.get(
        "/compare", params={"team_a": "Liverpool", "team_b": "Tottenham Hotspur"}
    )
    assert comparison.status_code == 200
    payload = comparison.json()
    assert abs(payload["euclidean_distance"] - 0.619924) < 1e-6
    assert len(payload["feature_differences"]) == 5


def test_unknown_team_returns_404() -> None:
    response = client.get("/teams/Not A Team/fingerprint")
    assert response.status_code == 404


def test_explain_success_uses_backend_result(monkeypatch) -> None:
    async def fake_generate(comparison: dict) -> tuple[str, str]:
        assert comparison["team_a"]["team"] == "Liverpool"
        assert comparison["team_b"]["team"] == "Tottenham Hotspur"
        return "Grounded test explanation.", "test/model"

    monkeypatch.setattr(main, "generate_explanation", fake_generate)
    response = client.post(
        "/explain",
        json={"team_a": "Liverpool", "team_b": "Tottenham Hotspur"},
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == "Grounded test explanation."


def test_explain_failure_does_not_affect_comparison(monkeypatch) -> None:
    async def fake_failure(comparison: dict) -> tuple[str, str]:
        raise RuntimeError("Featherless is not configured for this test")

    monkeypatch.setattr(main, "generate_explanation", fake_failure)
    failed = client.post(
        "/explain",
        json={"team_a": "Arsenal", "team_b": "Chelsea"},
    )
    assert failed.status_code == 503
    assert "not configured" in failed.json()["detail"]

    comparison = client.get(
        "/compare", params={"team_a": "Arsenal", "team_b": "Chelsea"}
    )
    assert comparison.status_code == 200


def test_explain_rate_limit_contains_ai_abuse(monkeypatch) -> None:
    async def fake_generate(comparison: dict) -> tuple[str, str]:
        return "Grounded test explanation.", "test/model"

    monkeypatch.setattr(main, "generate_explanation", fake_generate)
    monkeypatch.setattr(main, "EXPLAIN_RATE_LIMIT_REQUESTS", 2)
    payload = {"team_a": "Liverpool", "team_b": "Tottenham Hotspur"}

    assert client.post("/explain", json=payload).status_code == 200
    assert client.post("/explain", json=payload).status_code == 200
    limited = client.post("/explain", json=payload)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1

    comparison = client.get(
        "/compare", params={"team_a": "Liverpool", "team_b": "Tottenham Hotspur"}
    )
    assert comparison.status_code == 200


def test_explanation_evidence_contains_only_auditable_inputs() -> None:
    evidence = explanation_evidence(
        comparison_payload("Liverpool", "Tottenham Hotspur")
    )
    assert len(evidence["focal_team_features"]) == 5
    assert len(evidence["comparison_team_features"]) == 5
    assert len(evidence["signed_feature_differences"]) == 5
    assert len(evidence["metric_definitions"]) == 5
    assert len(evidence["known_model_limitations"]) == 4
    assert "Do not invent" in SYSTEM_PROMPT
    assert "Do not claim that either team is better" in SYSTEM_PROMPT
