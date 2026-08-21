import json
from collections import Counter
from pathlib import Path

import pandas as pd

from from_counter_possessions import classify_possessions


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATCHES_PATH = PROJECT_ROOT / "data/raw/statsbomb/matches/2-27.json"
EVENTS_DIR = PROJECT_ROOT / "data/raw/statsbomb/events"
OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/from_counter_possession_rate_2015_16.csv"
)
EXPECTED_MATCHES_PER_TEAM = 38

matches = json.loads(MATCHES_PATH.read_text())
expected_matches = Counter()
represented_matches = Counter()
eligible_possessions = Counter()
counter_possessions = Counter()
counter_then_regular = Counter()
edge_case_counts = Counter()

for match in matches:
    match_id = match["match_id"]
    home_team = match["home_team"]["home_team_name"]
    away_team = match["away_team"]["away_team_name"]
    match_teams = {home_team, away_team}
    expected_matches.update(match_teams)

    event_path = EVENTS_DIR / f"{match_id}.json"
    if not event_path.exists():
        continue

    events = json.loads(event_path.read_text())
    possessions = classify_possessions(events, match_id)
    eligible = possessions.loc[possessions["eligible"]]

    assert set(eligible["possession_team"]).issubset(match_teams)
    assert eligible["edge_case_flag"].eq("OK").all()
    assert eligible["possession_team"].ne(
        eligible["previous_possession_team"]
    ).all()
    assert eligible["initial_play_pattern"].isin(
        {"Regular Play", "From Counter"}
    ).all()

    represented_matches.update(match_teams)
    edge_case_counts.update(possessions["edge_case_flag"])

    for team, team_possessions in eligible.groupby("possession_team"):
        eligible_possessions[team] += len(team_possessions)
        team_counters = team_possessions.loc[
            team_possessions["is_from_counter"]
        ]
        counter_possessions[team] += len(team_counters)
        counter_then_regular[team] += int(
            team_counters["later_changes_to_regular_play"].sum()
        )

rows = []
for team in sorted(expected_matches):
    represented = represented_matches[team]
    expected = expected_matches[team]
    eligible_count = eligible_possessions[team]
    counter_count = counter_possessions[team]
    rate = (
        100 * counter_count / eligible_count
        if eligible_count
        else pd.NA
    )

    coverage_flag = (
        "OK"
        if represented == expected == EXPECTED_MATCHES_PER_TEAM
        else f"INCOMPLETE ({represented}/{expected})"
    )
    validation_flag = (
        "OK"
        if eligible_count > 0
        and 0 <= counter_count <= eligible_count
        and 0 <= rate <= 100
        else "SUSPICIOUS"
    )

    rows.append(
        {
            "team": team,
            "matches_represented": represented,
            "expected_matches": expected,
            "eligible_open_play_possession_changes": eligible_count,
            "from_counter_possessions": counter_count,
            "counter_possessions_later_regular": counter_then_regular[team],
            "from_counter_possession_rate": rate,
            "coverage_flag": coverage_flag,
            "validation_flag": validation_flag,
        }
    )

result = pd.DataFrame(rows).sort_values(
    "from_counter_possession_rate", ascending=False
)
result.insert(0, "rank", range(1, len(result) + 1))

assert len(result) == 20
assert result["coverage_flag"].eq("OK").all()
assert result["validation_flag"].eq("OK").all()
assert result["from_counter_possession_rate"].is_monotonic_decreasing

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_PATH, index=False, float_format="%.3f")

print(
    result.to_string(
        index=False,
        formatters={"from_counter_possession_rate": "{:.2f}".format},
    )
)
print("\nLEAGUE-WIDE POSSESSION CLASSIFICATION FLAGS")
print(pd.Series(edge_case_counts).sort_values(ascending=False).to_string())
