import json
from collections import Counter
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATCHES_PATH = PROJECT_ROOT / "data/raw/statsbomb/matches/2-27.json"
EVENTS_DIR = PROJECT_ROOT / "data/raw/statsbomb/events"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/mean_final_third_destination_width_2015_16.csv"
)
FINAL_THIRD_START_X = 80
PITCH_CENTRE_Y = 40
PITCH_WIDTH = 80
RESTART_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}
EXPECTED_MATCHES_PER_TEAM = 38

matches = json.loads(MATCHES_PATH.read_text())
expected_matches = Counter()
represented_matches = Counter()
pass_endpoints = Counter()
carry_endpoints = Counter()
lateral_distance_sum = Counter()

for match in matches:
    home_team = match["home_team"]["home_team_name"]
    away_team = match["away_team"]["away_team_name"]
    expected_matches.update((home_team, away_team))

    event_path = EVENTS_DIR / f"{match['match_id']}.json"
    if not event_path.exists():
        continue

    events_df = pd.json_normalize(json.loads(event_path.read_text()))
    all_passes = events_df.loc[events_df["type.name"].eq("Pass")]
    all_carries = events_df.loc[events_df["type.name"].eq("Carry")]

    assert all_passes["pass.end_location"].map(
        lambda location: isinstance(location, list) and len(location) >= 2
    ).all()
    assert all_carries["carry.end_location"].map(
        lambda location: isinstance(location, list) and len(location) >= 2
    ).all()

    passes = all_passes.loc[
        ~all_passes["pass.type.name"].isin(RESTART_PASS_TYPES)
    ].copy()
    passes["end_x"] = passes["pass.end_location"].str[0]
    passes["end_y"] = passes["pass.end_location"].str[1]
    passes = passes.loc[passes["end_x"].ge(FINAL_THIRD_START_X)].copy()
    passes["event_type"] = "Pass"

    carries = all_carries.copy()
    carries["end_x"] = carries["carry.end_location"].str[0]
    carries["end_y"] = carries["carry.end_location"].str[1]
    carries = carries.loc[carries["end_x"].ge(FINAL_THIRD_START_X)].copy()
    carries["event_type"] = "Carry"

    qualifying_events = pd.concat([passes, carries], ignore_index=True)
    qualifying_events["lateral_distance"] = (
        qualifying_events["end_y"] - PITCH_CENTRE_Y
    ).abs()
    qualifying_events["mirrored_lateral_distance"] = (
        PITCH_WIDTH - qualifying_events["end_y"] - PITCH_CENTRE_Y
    ).abs()

    assert qualifying_events[["end_x", "end_y"]].notna().all().all()
    assert qualifying_events["end_x"].ge(FINAL_THIRD_START_X).all()
    assert qualifying_events["end_y"].between(0, PITCH_WIDTH).all()
    assert not passes["pass.type.name"].isin(RESTART_PASS_TYPES).any()
    assert (
        qualifying_events["lateral_distance"]
        - qualifying_events["mirrored_lateral_distance"]
    ).abs().max() < 1e-9

    represented_matches.update((home_team, away_team))
    for team, team_events in qualifying_events.groupby("team.name"):
        pass_endpoints[team] += int(team_events["event_type"].eq("Pass").sum())
        carry_endpoints[team] += int(team_events["event_type"].eq("Carry").sum())
        lateral_distance_sum[team] += team_events["lateral_distance"].sum()

rows = []
for team in sorted(expected_matches):
    represented = represented_matches[team]
    expected = expected_matches[team]
    pass_count = pass_endpoints[team]
    carry_count = carry_endpoints[team]
    total_endpoints = pass_count + carry_count
    mean_width = (
        lateral_distance_sum[team] / total_endpoints
        if total_endpoints
        else pd.NA
    )

    coverage_flag = (
        "OK"
        if represented == expected == EXPECTED_MATCHES_PER_TEAM
        else f"INCOMPLETE ({represented}/{expected})"
    )
    data_quality_flag = (
        "OK"
        if total_endpoints > 0
        and pass_count > 0
        and carry_count > 0
        and 0 <= mean_width <= 40
        else "SUSPICIOUS"
    )

    rows.append(
        {
            "team": team,
            "matches_represented": represented,
            "expected_matches": expected,
            "qualifying_pass_endpoints": pass_count,
            "qualifying_carry_endpoints": carry_count,
            "total_qualifying_endpoints": total_endpoints,
            "mean_final_third_destination_width": mean_width,
            "coverage_flag": coverage_flag,
            "data_quality_flag": data_quality_flag,
        }
    )

result = pd.DataFrame(rows).sort_values(
    "mean_final_third_destination_width", ascending=False
)
result.insert(0, "rank", range(1, len(result) + 1))

assert len(result) == 20
assert result["coverage_flag"].eq("OK").all()
assert result["data_quality_flag"].eq("OK").all()
assert result["mean_final_third_destination_width"].is_monotonic_decreasing

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_PATH, index=False, float_format="%.3f")

print(
    result.to_string(
        index=False,
        formatters={"mean_final_third_destination_width": "{:.2f}".format},
    )
)
