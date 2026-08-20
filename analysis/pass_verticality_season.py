import json
from collections import Counter
from math import cos
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATCHES_PATH = PROJECT_ROOT / "data/raw/statsbomb/matches/2-27.json"
EVENTS_DIR = PROJECT_ROOT / "data/raw/statsbomb/events"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/pass_verticality_2015_16.csv"
RESTART_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}
EXPECTED_MATCHES_PER_TEAM = 38

matches = json.loads(MATCHES_PATH.read_text())
expected_matches = Counter()
represented_matches = Counter()
attempted_passes = Counter()
unsuccessful_passes = Counter()
net_forward_distance = Counter()
total_pass_distance = Counter()
angle_net_forward_distance = Counter()

for match in matches:
    home_team = match["home_team"]["home_team_name"]
    away_team = match["away_team"]["away_team_name"]
    expected_matches.update((home_team, away_team))

    event_path = EVENTS_DIR / f"{match['match_id']}.json"
    if not event_path.exists():
        continue

    events_df = pd.json_normalize(json.loads(event_path.read_text()))
    passes = events_df.loc[
        events_df["type.name"].eq("Pass")
        & ~events_df["pass.type.name"].isin(RESTART_PASS_TYPES)
    ].copy()

    passes["start_x"] = passes["location"].str[0]
    passes["end_x"] = passes["pass.end_location"].str[0]
    passes["forward_distance"] = passes["end_x"] - passes["start_x"]
    passes["angle_forward_distance"] = (
        passes["pass.length"] * passes["pass.angle"].map(cos)
    )

    assert not passes["pass.type.name"].isin(RESTART_PASS_TYPES).any()
    assert passes[
        ["start_x", "end_x", "pass.length", "pass.angle"]
    ].notna().all().all()

    represented_matches.update((home_team, away_team))
    for team, team_passes in passes.groupby("team.name"):
        attempted_passes[team] += len(team_passes)
        unsuccessful_passes[team] += team_passes["pass.outcome.name"].count()
        net_forward_distance[team] += team_passes["forward_distance"].sum()
        total_pass_distance[team] += team_passes["pass.length"].sum()
        angle_net_forward_distance[team] += team_passes[
            "angle_forward_distance"
        ].sum()

rows = []
for team in sorted(expected_matches):
    represented = represented_matches[team]
    expected = expected_matches[team]
    distance = total_pass_distance[team]
    coordinate_numerator = net_forward_distance[team]

    if represented == expected == EXPECTED_MATCHES_PER_TEAM:
        coverage_flag = "OK"
    else:
        coverage_flag = f"INCOMPLETE ({represented}/{expected})"

    rows.append(
        {
            "team": team,
            "matches_represented": represented,
            "expected_matches": expected,
            "eligible_pass_attempts": attempted_passes[team],
            "unsuccessful_pass_attempts": unsuccessful_passes[team],
            "net_forward_distance": coordinate_numerator,
            "total_pass_distance": distance,
            "pass_verticality": (
                coordinate_numerator / distance if distance else pd.NA
            ),
            "pass_verticality_pct": (
                100 * coordinate_numerator / distance if distance else pd.NA
            ),
            "angle_validation_difference": abs(
                coordinate_numerator - angle_net_forward_distance[team]
            ),
            "coverage_flag": coverage_flag,
        }
    )

result = pd.DataFrame(rows).sort_values("pass_verticality", ascending=False)
result.insert(0, "rank", range(1, len(result) + 1))

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_PATH, index=False, float_format="%.4f")

print(
    result.to_string(
        index=False,
        formatters={
            "net_forward_distance": "{:.1f}".format,
            "total_pass_distance": "{:.1f}".format,
            "pass_verticality": "{:.3f}".format,
            "pass_verticality_pct": "{:.1f}".format,
            "angle_validation_difference": "{:.4f}".format,
        },
    )
)
