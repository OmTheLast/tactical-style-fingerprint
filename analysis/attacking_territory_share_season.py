import json
from collections import Counter
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATCHES_PATH = PROJECT_ROOT / "data/raw/statsbomb/matches/2-27.json"
EVENTS_DIR = PROJECT_ROOT / "data/raw/statsbomb/events"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/attacking_territory_share_2015_16.csv"
FINAL_THIRD_START_X = 80
EXPECTED_MATCHES_PER_TEAM = 38


matches = json.loads(MATCHES_PATH.read_text())
expected_matches = Counter()
represented_matches = Counter()
team_passes = Counter()
opponent_passes = Counter()

for match in matches:
    home_team = match["home_team"]["home_team_name"]
    away_team = match["away_team"]["away_team_name"]
    expected_matches.update((home_team, away_team))

    event_path = EVENTS_DIR / f"{match['match_id']}.json"
    if not event_path.exists():
        continue

    events = json.loads(event_path.read_text())
    events_df = pd.json_normalize(events)
    events_df["x"] = events_df["location"].str[0]

    qualifying_passes = events_df.loc[
        events_df["type.name"].eq("Pass")
        & events_df["pass.outcome.name"].isna()
        & events_df["x"].ge(FINAL_THIRD_START_X)
    ]
    match_counts = qualifying_passes.groupby("team.name").size()
    home_count = int(match_counts.get(home_team, 0))
    away_count = int(match_counts.get(away_team, 0))

    represented_matches.update((home_team, away_team))
    team_passes[home_team] += home_count
    team_passes[away_team] += away_count
    opponent_passes[home_team] += away_count
    opponent_passes[away_team] += home_count

rows = []
for team in sorted(expected_matches):
    own = team_passes[team]
    opponents = opponent_passes[team]
    denominator = own + opponents
    represented = represented_matches[team]
    expected = expected_matches[team]

    if represented == expected == EXPECTED_MATCHES_PER_TEAM:
        coverage_flag = "OK"
    else:
        coverage_flag = f"INCOMPLETE ({represented}/{expected})"

    rows.append(
        {
            "team": team,
            "matches_represented": represented,
            "expected_matches": expected,
            "qualifying_team_passes": own,
            "qualifying_opponent_passes": opponents,
            "attacking_territory_share_pct": (
                100 * own / denominator if denominator else pd.NA
            ),
            "coverage_flag": coverage_flag,
        }
    )

result = pd.DataFrame(rows).sort_values(
    "attacking_territory_share_pct", ascending=False
)
result.insert(0, "rank", range(1, len(result) + 1))

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_PATH, index=False, float_format="%.1f")

print(
    result.to_string(
        index=False,
        formatters={"attacking_territory_share_pct": "{:.1f}".format},
    )
)
