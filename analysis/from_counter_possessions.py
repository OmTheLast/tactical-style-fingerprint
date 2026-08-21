from collections import defaultdict

import pandas as pd


MEANINGFUL_ON_BALL_TYPES = {
    "50/50",
    "Ball Receipt*",
    "Ball Recovery",
    "Carry",
    "Clearance",
    "Dispossessed",
    "Dribble",
    "Duel",
    "Goal Keeper",
    "Interception",
    "Miscontrol",
    "Pass",
    "Shield",
    "Shot",
}
OPEN_PLAY_PATTERNS = {"Regular Play", "From Counter"}


def classify_possessions(events, match_id):
    """Return one classification row per StatsBomb possession and period."""
    events = sorted(events, key=lambda event: event["index"])
    period_keys = defaultdict(list)
    possession_events = defaultdict(list)

    for event in events:
        key = (event["period"], event["possession"])
        if key not in possession_events:
            period_keys[event["period"]].append(key)
        possession_events[key].append(event)

    rows = []
    for period, keys in period_keys.items():
        previous_possession_team = None

        for position_in_period, key in enumerate(keys):
            group = possession_events[key]
            possession_team = group[0]["possession_team"]
            assert all(
                event["possession_team"]["id"] == possession_team["id"]
                for event in group
            )

            meaningful_event = next(
                (
                    event
                    for event in group
                    if event.get("team", {}).get("id") == possession_team["id"]
                    and event["type"]["name"] in MEANINGFUL_ON_BALL_TYPES
                ),
                None,
            )

            first_in_period = position_in_period == 0
            team_changed = (
                not first_in_period
                and possession_team["id"] != previous_possession_team["id"]
            )
            initial_pattern = (
                meaningful_event["play_pattern"]["name"]
                if meaningful_event
                else None
            )
            eligible = (
                not first_in_period
                and team_changed
                and meaningful_event is not None
                and initial_pattern in OPEN_PLAY_PATTERNS
            )

            if first_in_period:
                edge_case_flag = "FIRST_POSSESSION_OF_PERIOD"
            elif not team_changed:
                edge_case_flag = "SAME_TEAM_AS_PREVIOUS"
            elif meaningful_event is None:
                edge_case_flag = "NO_MEANINGFUL_ON_BALL_EVENT"
            elif initial_pattern not in OPEN_PLAY_PATTERNS:
                edge_case_flag = f"NON_OPEN_PLAY: {initial_pattern}"
            else:
                edge_case_flag = "OK"

            patterns = {event["play_pattern"]["name"] for event in group}
            rows.append(
                {
                    "match_id": match_id,
                    "period": period,
                    "possession": key[1],
                    "possession_team": possession_team["name"],
                    "previous_possession_team": (
                        previous_possession_team["name"]
                        if previous_possession_team
                        else None
                    ),
                    "initial_event_index": (
                        meaningful_event["index"] if meaningful_event else pd.NA
                    ),
                    "initial_timestamp": (
                        meaningful_event["timestamp"] if meaningful_event else pd.NA
                    ),
                    "initial_event_type": (
                        meaningful_event["type"]["name"]
                        if meaningful_event
                        else pd.NA
                    ),
                    "initial_player": (
                        meaningful_event.get("player", {}).get("name", "Unknown")
                        if meaningful_event
                        else pd.NA
                    ),
                    "initial_location": (
                        meaningful_event.get("location", pd.NA)
                        if meaningful_event
                        else pd.NA
                    ),
                    "initial_play_pattern": initial_pattern,
                    "event_count": len(group),
                    "later_changes_to_regular_play": (
                        initial_pattern == "From Counter" and "Regular Play" in patterns
                    ),
                    "eligible": eligible,
                    "is_from_counter": (
                        eligible and initial_pattern == "From Counter"
                    ),
                    "edge_case_flag": edge_case_flag,
                }
            )
            previous_possession_team = possession_team

    result = pd.DataFrame(rows)
    assert not result.duplicated(["match_id", "period", "possession"]).any()
    return result
