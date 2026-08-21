import json
from pathlib import Path

import pandas as pd


MATCH_PATH = (
    Path(__file__).resolve().parents[1]
    / "data/raw/statsbomb/events/3754097.json"
)
FINAL_THIRD_START_X = 80
PITCH_CENTRE_Y = 40
PITCH_WIDTH = 80
RESTART_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}

events = json.loads(MATCH_PATH.read_text())
events_df = pd.json_normalize(events)

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

result = qualifying_events.groupby("team.name").agg(
    qualifying_pass_endpoints=("event_type", lambda values: values.eq("Pass").sum()),
    qualifying_carry_endpoints=("event_type", lambda values: values.eq("Carry").sum()),
    total_qualifying_endpoints=("id", "size"),
    mean_final_third_destination_width=("lateral_distance", "mean"),
)

examples = (
    qualifying_events.sort_values(["team.name", "event_type", "index"])
    .groupby(["team.name", "event_type"])
    .head(2)
    .loc[
        :,
        [
            "team.name",
            "event_type",
            "timestamp",
            "player.name",
            "end_x",
            "end_y",
            "lateral_distance",
        ],
    ]
)

print("RESULT")
print(
    result.to_string(
        formatters={"mean_final_third_destination_width": "{:.2f}".format}
    )
)
print("\nEXAMPLE QUALIFYING EVENTS")
print(
    examples.to_string(
        index=False,
        formatters={
            "end_x": "{:.1f}".format,
            "end_y": "{:.1f}".format,
            "lateral_distance": "{:.1f}".format,
        },
    )
)
print("\nSymmetry check passed: |y - 40| = |(80 - y) - 40| for every row.")
