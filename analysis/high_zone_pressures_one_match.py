import json
from pathlib import Path

import pandas as pd


MATCH_PATH = (
    Path(__file__).resolve().parents[1]
    / "data/raw/statsbomb/events/3754097.json"
)
HIGH_ZONE_START_X = 48
OPPONENT_BUILDUP_END_X = 72
RESTART_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}

events = json.loads(MATCH_PATH.read_text())
events_df = pd.json_normalize(events)
teams = sorted(events_df["team.name"].dropna().unique())
assert len(teams) == 2

qualifying_pressures = events_df.loc[
    events_df["type.name"].eq("Pressure")
    & events_df["location"].str[0].ge(HIGH_ZONE_START_X)
].copy()
qualifying_pressures["x"] = qualifying_pressures["location"].str[0]

qualifying_passes = events_df.loc[
    events_df["type.name"].eq("Pass")
    & events_df["location"].str[0].le(OPPONENT_BUILDUP_END_X)
    & ~events_df["pass.type.name"].isin(RESTART_PASS_TYPES)
].copy()
qualifying_passes["x"] = qualifying_passes["location"].str[0]

pressure_counts = qualifying_pressures.groupby("team.name").size()
pass_counts = qualifying_passes.groupby("team.name").size()

rows = []
for team in teams:
    opponent = next(other_team for other_team in teams if other_team != team)
    numerator = int(pressure_counts.get(team, 0))
    denominator = int(pass_counts.get(opponent, 0))
    rows.append(
        {
            "team": team,
            "qualifying_high_zone_pressures": numerator,
            "qualifying_opposition_passes": denominator,
            "high_zone_pressures_per_100_opposition_passes": (
                100 * numerator / denominator if denominator else pd.NA
            ),
        }
    )

result = pd.DataFrame(rows).sort_values(
    "high_zone_pressures_per_100_opposition_passes", ascending=False
)

assert qualifying_pressures["x"].ge(HIGH_ZONE_START_X).all()
assert qualifying_passes["x"].le(OPPONENT_BUILDUP_END_X).all()
assert not qualifying_passes["pass.type.name"].isin(RESTART_PASS_TYPES).any()

pressure_examples = qualifying_pressures.loc[
    :, ["team.name", "possession_team.name", "timestamp", "player.name", "location"]
].groupby("team.name").head(2)
same_possession_team_example = qualifying_pressures.loc[
    qualifying_pressures["team.name"].eq(
        qualifying_pressures["possession_team.name"]
    ),
    ["team.name", "possession_team.name", "timestamp", "player.name", "location"],
].head(1)

pass_examples = qualifying_passes.loc[
    :,
    [
        "team.name",
        "timestamp",
        "player.name",
        "location",
        "pass.end_location",
        "pass.outcome.name",
        "pass.type.name",
    ],
].groupby("team.name").head(2)
pass_examples["pass.outcome.name"] = pass_examples["pass.outcome.name"].fillna(
    "Complete"
)
pass_examples["pass.type.name"] = pass_examples["pass.type.name"].fillna(
    "Regular"
)

print("RESULT")
print(
    result.to_string(
        index=False,
        formatters={
            "high_zone_pressures_per_100_opposition_passes": "{:.1f}".format
        },
    )
)
print("\nEXAMPLE QUALIFYING PRESSURES (x >= 48 in pressure-team coordinates)")
print(pressure_examples.to_string(index=False))
print("\nQUALIFYING PRESSURE WHERE TEAM EQUALS POSSESSION_TEAM")
print(same_possession_team_example.to_string(index=False))
print("\nEXAMPLE QUALIFYING OPPOSITION PASSES (x <= 72 in passer coordinates)")
print(pass_examples.to_string(index=False))
