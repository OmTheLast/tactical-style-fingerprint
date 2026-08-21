import json
from pathlib import Path

import pandas as pd

from from_counter_possessions import classify_possessions


MATCH_ID = 3754097
MATCH_PATH = (
    Path(__file__).resolve().parents[1]
    / f"data/raw/statsbomb/events/{MATCH_ID}.json"
)

events = json.loads(MATCH_PATH.read_text())
possessions = classify_possessions(events, MATCH_ID)
eligible = possessions.loc[possessions["eligible"]].copy()

assert eligible["edge_case_flag"].eq("OK").all()
assert eligible["possession_team"].ne(
    eligible["previous_possession_team"]
).all()
assert eligible["initial_play_pattern"].isin(
    {"Regular Play", "From Counter"}
).all()
assert eligible.loc[eligible["is_from_counter"], "initial_play_pattern"].eq(
    "From Counter"
).all()

result = eligible.groupby("possession_team").agg(
    eligible_open_play_possession_changes=("possession", "size"),
    from_counter_possessions=("is_from_counter", "sum"),
)
result["from_counter_possession_rate"] = (
    100
    * result["from_counter_possessions"]
    / result["eligible_open_play_possession_changes"]
)
result = result.sort_values("from_counter_possession_rate", ascending=False)

counter_examples = eligible.loc[eligible["is_from_counter"]]
regular_examples = (
    eligible.loc[~eligible["is_from_counter"]]
    .groupby("possession_team")
    .head(2)
)
examples = pd.concat([counter_examples, regular_examples]).sort_values(
    ["period", "possession"]
)

example_columns = [
    "period",
    "possession",
    "possession_team",
    "previous_possession_team",
    "initial_timestamp",
    "initial_event_type",
    "initial_player",
    "initial_location",
    "initial_play_pattern",
    "event_count",
    "later_changes_to_regular_play",
]

print("RESULT")
print(
    result.to_string(
        formatters={"from_counter_possession_rate": "{:.2f}".format}
    )
)
print("\nCOUNTER AND REGULAR EXAMPLES")
print(examples.loc[:, example_columns].to_string(index=False))
print("\nEXCLUDED POSSESSION EDGE CASES")
print(possessions["edge_case_flag"].value_counts().to_string())
