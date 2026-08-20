import json
from math import cos
from pathlib import Path

import pandas as pd


MATCH_PATH = (
    Path(__file__).resolve().parents[1]
    / "data/raw/statsbomb/events/3754097.json"
)
RESTART_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}

events = json.loads(MATCH_PATH.read_text())
events_df = pd.json_normalize(events)

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

result = passes.groupby("team.name").agg(
    attempted_passes=("id", "size"),
    unsuccessful_passes=("pass.outcome.name", "count"),
    net_forward_distance=("forward_distance", "sum"),
    total_pass_distance=("pass.length", "sum"),
    angle_net_forward_distance=("angle_forward_distance", "sum"),
)
result["pass_verticality"] = (
    result["net_forward_distance"] / result["total_pass_distance"]
)
result["pass_verticality_pct"] = 100 * result["pass_verticality"]
result["angle_validation_difference"] = (
    result["net_forward_distance"] - result["angle_net_forward_distance"]
).abs()

assert not passes["pass.type.name"].isin(RESTART_PASS_TYPES).any()
assert passes[["start_x", "end_x", "pass.length", "pass.angle"]].notna().all().all()

print(
    result.to_string(
        formatters={
            "net_forward_distance": "{:.1f}".format,
            "total_pass_distance": "{:.1f}".format,
            "angle_net_forward_distance": "{:.1f}".format,
            "pass_verticality": "{:.3f}".format,
            "pass_verticality_pct": "{:.1f}".format,
            "angle_validation_difference": "{:.4f}".format,
        }
    )
)
