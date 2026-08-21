import json
from collections import Counter
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATCHES_PATH = PROJECT_ROOT / "data/raw/statsbomb/matches/2-27.json"
EVENTS_DIR = PROJECT_ROOT / "data/raw/statsbomb/events"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/high_zone_pressures_per_100_opposition_passes_2015_16.csv"
)
HIGH_ZONE_START_X = 48
OPPONENT_BUILDUP_END_X = 72
RESTART_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}
EXPECTED_MATCHES_PER_TEAM = 38

matches = json.loads(MATCHES_PATH.read_text())
expected_matches = Counter()
represented_matches = Counter()
high_zone_pressures = Counter()
opposition_passes = Counter()

for match in matches:
    home_team = match["home_team"]["home_team_name"]
    away_team = match["away_team"]["away_team_name"]
    expected_matches.update((home_team, away_team))

    event_path = EVENTS_DIR / f"{match['match_id']}.json"
    if not event_path.exists():
        continue

    events_df = pd.json_normalize(json.loads(event_path.read_text()))
    event_x = events_df["location"].str[0]

    qualifying_pressures = events_df.loc[
        events_df["type.name"].eq("Pressure")
        & event_x.ge(HIGH_ZONE_START_X)
    ]
    qualifying_passes = events_df.loc[
        events_df["type.name"].eq("Pass")
        & event_x.le(OPPONENT_BUILDUP_END_X)
        & ~events_df["pass.type.name"].isin(RESTART_PASS_TYPES)
    ]

    assert qualifying_pressures["location"].str[0].ge(HIGH_ZONE_START_X).all()
    assert qualifying_passes["location"].str[0].le(OPPONENT_BUILDUP_END_X).all()
    assert not qualifying_passes["pass.type.name"].isin(RESTART_PASS_TYPES).any()

    pressure_counts = qualifying_pressures.groupby("team.name").size()
    pass_counts = qualifying_passes.groupby("team.name").size()
    home_passes = int(pass_counts.get(home_team, 0))
    away_passes = int(pass_counts.get(away_team, 0))

    represented_matches.update((home_team, away_team))
    high_zone_pressures[home_team] += int(pressure_counts.get(home_team, 0))
    high_zone_pressures[away_team] += int(pressure_counts.get(away_team, 0))
    opposition_passes[home_team] += away_passes
    opposition_passes[away_team] += home_passes

rows = []
for team in sorted(expected_matches):
    represented = represented_matches[team]
    expected = expected_matches[team]
    numerator = high_zone_pressures[team]
    denominator = opposition_passes[team]

    if represented == expected == EXPECTED_MATCHES_PER_TEAM:
        coverage_flag = "OK"
    else:
        coverage_flag = f"INCOMPLETE ({represented}/{expected})"

    rows.append(
        {
            "team": team,
            "matches_represented": represented,
            "expected_matches": expected,
            "qualifying_high_zone_pressures": numerator,
            "qualifying_opposition_passes": denominator,
            "high_zone_pressures_per_100_opposition_passes": (
                100 * numerator / denominator if denominator else pd.NA
            ),
            "coverage_flag": coverage_flag,
        }
    )

result = pd.DataFrame(rows).sort_values(
    "high_zone_pressures_per_100_opposition_passes", ascending=False
)
result.insert(0, "rank", range(1, len(result) + 1))

assert len(result) == 20
assert result["coverage_flag"].eq("OK").all()
assert result["qualifying_opposition_passes"].gt(0).all()
assert result["high_zone_pressures_per_100_opposition_passes"].is_monotonic_decreasing

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_PATH, index=False, float_format="%.3f")

print(
    result.to_string(
        index=False,
        formatters={
            "high_zone_pressures_per_100_opposition_passes": "{:.1f}".format
        },
    )
)
