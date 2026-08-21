import json
from pathlib import Path

import pandas as pd


MATCH_PATH = (
    Path(__file__).resolve().parents[1]
    / "data/raw/statsbomb/events/3754097.json"
)
FINAL_THIRD_START_X = 80

events = json.loads(MATCH_PATH.read_text())
events_df = pd.json_normalize(events)
events_df["x"] = events_df["location"].str[0]

final_third_completed_passes = events_df.loc[
    events_df["type.name"].eq("Pass")
    & events_df["pass.outcome.name"].isna()
    & events_df["x"].ge(FINAL_THIRD_START_X)
]

result = (
    final_third_completed_passes.groupby("team.name")
    .size()
    .rename("completed_final_third_passes")
    .to_frame()
)
result["attacking_territory_share_pct"] = (
    100 * result["completed_final_third_passes"]
    / result["completed_final_third_passes"].sum()
)

print(result.round({"attacking_territory_share_pct": 1}))
