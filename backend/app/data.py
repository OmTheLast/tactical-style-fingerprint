from functools import lru_cache
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data/processed"
FINGERPRINT_PATH = (
    PROCESSED_DIR
    / "premier_league_2015_16_standardized_tactical_fingerprints.csv"
)
PAIRWISE_PATH = (
    PROCESSED_DIR / "premier_league_2015_16_pairwise_tactical_distances.csv"
)

SEASON_LABEL = "Premier League 2015/16"

FEATURES = [
    {
        "key": "attacking_territory",
        "label": "Attacking Territory",
        "raw_name": "Attacking Territory Share",
        "raw_column": "attacking_territory_share_pct",
        "z_column": "attacking_territory_z",
        "unit": "% share",
        "definition": (
            "Share of both teams' completed, non-restart passes that start in "
            "the team's attacking third."
        ),
        "high_meaning": "More of the selected final-third passing belonged to the team.",
        "limitation": (
            "A completed-pass proxy for territory; it is not possession time or "
            "tracking-derived territorial control."
        ),
    },
    {
        "key": "pass_verticality",
        "label": "Pass Verticality",
        "raw_name": "Pass Verticality",
        "raw_column": "pass_verticality",
        "z_column": "pass_verticality_z",
        "unit": "forward share",
        "definition": (
            "Net forward pass distance divided by total pass distance across "
            "non-restart attempted passes."
        ),
        "high_meaning": "Passing attempts point more directly toward goal.",
        "limitation": (
            "Measures directional intent, not possession speed, chance quality, "
            "or whether the passes succeeded."
        ),
    },
    {
        "key": "pressing_intensity",
        "label": "Pressing Intensity",
        "raw_name": "High-Zone Pressures per 100 Opposition Passes",
        "raw_column": "high_zone_pressures_per_100_opposition_passes",
        "z_column": "pressing_intensity_z",
        "unit": "per 100 passes",
        "definition": (
            "Recorded high-zone Pressure events per 100 qualifying opposition "
            "pass attempts."
        ),
        "high_meaning": "More recorded pressure activity high up the pitch.",
        "limitation": (
            "Measures pressure activity, not press success, team compactness, or "
            "the full defensive structure."
        ),
    },
    {
        "key": "attacking_width",
        "label": "Attacking Width",
        "raw_name": "Mean Final-Third Destination Width",
        "raw_column": "mean_final_third_destination_width",
        "z_column": "attacking_width_z",
        "unit": "pitch units",
        "definition": (
            "Mean distance from the centre line, abs(end_y - 40), for eligible "
            "Pass and Carry endpoints in the final third."
        ),
        "high_meaning": "Recorded advanced ball destinations tend to be wider.",
        "limitation": (
            "Does not measure formation width or off-ball player positions; its "
            "narrow raw range is expanded by standardization."
        ),
    },
    {
        "key": "counterattacking_tendency",
        "label": "Counterattacking Tendency",
        "raw_name": "From-Counter Possession Rate",
        "raw_column": "from_counter_possession_rate",
        "z_column": "counterattacking_tendency_z",
        "unit": "per 100 changes",
        "definition": (
            "Provider-labelled From Counter possessions per 100 eligible "
            "open-play possession changes."
        ),
        "high_meaning": "More eligible possessions begin as annotated counters.",
        "limitation": (
            "Relies on StatsBomb's provider-defined From Counter annotation and "
            "is affected by the transition opportunities opponents allow."
        ),
    },
]

MODEL_LIMITATIONS = [
    (
        "Attacking Territory and Pass Verticality correlate at -0.839, so the "
        "fingerprint may partly double-weight a control-versus-directness axis."
    ),
    (
        "Attacking Width has a narrow raw range, and removing it materially "
        "changed several nearest-neighbour rankings."
    ),
    (
        "Five event-data-derived dimensions cannot represent the full tactical "
        "behaviour of a football team."
    ),
    (
        "A nearest team is only the least distant available team; it is not "
        "necessarily a very close tactical match."
    ),
]

DISPLAY_SCALE_NOTE = (
    "Visualization only: 0 is the lowest and 100 the highest observed value "
    "among the 20 Premier League 2015/16 teams. These are league-relative "
    "positions, not quality scores, probabilities, or objective limits."
)


@lru_cache(maxsize=1)
def load_fingerprints() -> pd.DataFrame:
    frame = pd.read_csv(FINGERPRINT_PATH).sort_values("team").reset_index(drop=True)
    required = {"team"}
    for feature in FEATURES:
        required.update({feature["raw_column"], feature["z_column"]})
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"Fingerprint data is missing columns: {sorted(missing)}")
    if len(frame) != 20 or frame["team"].nunique() != 20:
        raise RuntimeError("Expected exactly 20 unique teams in fingerprint data")
    if frame[list(required)].isna().any().any():
        raise RuntimeError("Fingerprint data contains missing values")
    return frame


@lru_cache(maxsize=1)
def load_pairwise() -> pd.DataFrame:
    frame = pd.read_csv(PAIRWISE_PATH)
    if len(frame) != 380 or not frame.groupby("team").size().eq(19).all():
        raise RuntimeError("Expected 19 pairwise comparisons for each of 20 teams")
    return frame


def team_names() -> list[str]:
    return load_fingerprints()["team"].tolist()


def require_team(team: str) -> pd.Series:
    matches = load_fingerprints().loc[load_fingerprints()["team"] == team]
    if matches.empty:
        raise KeyError(team)
    return matches.iloc[0]


def display_value(raw_column: str, value: float) -> float:
    values = load_fingerprints()[raw_column]
    feature_range = values.max() - values.min()
    if feature_range == 0:
        return 50.0
    return 100 * (value - values.min()) / feature_range


def fingerprint_payload(team: str) -> dict:
    row = require_team(team)
    features = []
    for feature in FEATURES:
        raw_value = float(row[feature["raw_column"]])
        features.append(
            {
                "key": feature["key"],
                "label": feature["label"],
                "raw_metric_name": feature["raw_name"],
                "raw_value": raw_value,
                "raw_unit": feature["unit"],
                "z_score": float(row[feature["z_column"]]),
                "display_value": display_value(feature["raw_column"], raw_value),
                "definition": feature["definition"],
                "high_meaning": feature["high_meaning"],
                "limitation": feature["limitation"],
            }
        )
    return {
        "team": team,
        "season": SEASON_LABEL,
        "features": features,
        "display_scale_note": DISPLAY_SCALE_NOTE,
        "model_limitations": MODEL_LIMITATIONS,
    }


def comparison_payload(team_a: str, team_b: str) -> dict:
    require_team(team_a)
    require_team(team_b)
    if team_a == team_b:
        distance = 0.0
        differences = [
            {
                "key": feature["key"],
                "label": feature["label"],
                "signed_z_difference": 0.0,
                "absolute_z_difference": 0.0,
            }
            for feature in FEATURES
        ]
    else:
        matches = load_pairwise().loc[
            (load_pairwise()["team"] == team_a)
            & (load_pairwise()["comparison_team"] == team_b)
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Missing unique comparison for {team_a} and {team_b}")
        row = matches.iloc[0]
        distance = float(row["euclidean_distance"])
        differences = [
            {
                "key": feature["key"],
                "label": feature["label"],
                "signed_z_difference": float(
                    row[f"{feature['key']}_z_difference"]
                ),
                "absolute_z_difference": float(
                    row[f"{feature['key']}_absolute_z_difference"]
                ),
            }
            for feature in FEATURES
        ]

    return {
        "team_a": fingerprint_payload(team_a),
        "team_b": fingerprint_payload(team_b),
        "euclidean_distance": distance,
        "feature_differences": differences,
        "distance_note": (
            "Smaller means closer across the five equally weighted z-scored "
            "features. It is not a probability or percentage."
        ),
    }


def neighbours_payload(team: str, limit: int = 5) -> dict:
    require_team(team)
    comparisons = (
        load_pairwise()
        .loc[load_pairwise()["team"] == team]
        .sort_values(["euclidean_distance", "comparison_team"])
        .head(limit)
    )
    neighbours = []
    for _, row in comparisons.iterrows():
        differences = [
            {
                "key": feature["key"],
                "label": feature["label"],
                "signed_z_difference": float(
                    row[f"{feature['key']}_z_difference"]
                ),
                "absolute_z_difference": float(
                    row[f"{feature['key']}_absolute_z_difference"]
                ),
            }
            for feature in FEATURES
        ]
        ordered = sorted(differences, key=lambda item: item["absolute_z_difference"])
        neighbours.append(
            {
                "team": row["comparison_team"],
                "euclidean_distance": float(row["euclidean_distance"]),
                "closest_dimensions": [item["label"] for item in ordered[:2]],
                "different_dimensions": [item["label"] for item in ordered[-2:][::-1]],
                "feature_differences": differences,
            }
        )
    return {
        "team": team,
        "neighbours": neighbours,
        "distance_note": (
            "Ranked by five-feature z-score Euclidean distance. Nearest does not "
            "necessarily mean very close."
        ),
    }
