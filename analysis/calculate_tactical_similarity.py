from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data/processed"
INPUT_PATH = (
    PROCESSED_DIR / "premier_league_2015_16_raw_tactical_fingerprints.csv"
)

STANDARDIZED_OUTPUT_PATH = (
    PROCESSED_DIR
    / "premier_league_2015_16_standardized_tactical_fingerprints.csv"
)
PAIRWISE_OUTPUT_PATH = (
    PROCESSED_DIR / "premier_league_2015_16_pairwise_tactical_distances.csv"
)
NEIGHBOURS_OUTPUT_PATH = (
    PROCESSED_DIR / "premier_league_2015_16_nearest_5_tactical_neighbours.csv"
)
SENSITIVITY_OUTPUT_PATH = (
    PROCESSED_DIR / "premier_league_2015_16_similarity_sensitivity_checks.csv"
)

FEATURES = {
    "attacking_territory": "attacking_territory_share_pct",
    "pass_verticality": "pass_verticality",
    "pressing_intensity": "high_zone_pressures_per_100_opposition_passes",
    "attacking_width": "mean_final_third_destination_width",
    "counterattacking_tendency": "from_counter_possession_rate",
}
RAW_COLUMNS = list(FEATURES.values())


def euclidean_distance_matrix(values: np.ndarray) -> np.ndarray:
    differences = values[:, np.newaxis, :] - values[np.newaxis, :, :]
    return np.sqrt(np.sum(differences**2, axis=2))


def ordered_neighbours(
    distance_matrix: np.ndarray, teams: list[str], limit: int
) -> dict[str, list[str]]:
    result = {}
    for team_index, team in enumerate(teams):
        order = np.argsort(distance_matrix[team_index], kind="stable")
        other_indices = [index for index in order if index != team_index]
        result[team] = [teams[index] for index in other_indices[:limit]]
    return result


raw = pd.read_csv(INPUT_PATH).sort_values("team").reset_index(drop=True)
assert len(raw) == 20
assert raw["team"].nunique() == 20
assert not raw[["team", *RAW_COLUMNS]].isna().any().any()

# pandas operates column by column here. ddof=0 selects the population standard
# deviation specified for this complete 20-team league population.
feature_means = raw[RAW_COLUMNS].mean()
feature_stds = raw[RAW_COLUMNS].std(ddof=0)
assert feature_stds.gt(0).all()

z_values = (raw[RAW_COLUMNS] - feature_means) / feature_stds
z_values.columns = [f"{feature_name}_z" for feature_name in FEATURES]
Z_COLUMNS = z_values.columns.tolist()

standardized = pd.concat([raw[["team", *RAW_COLUMNS]], z_values], axis=1)
standardized.to_csv(STANDARDIZED_OUTPUT_PATH, index=False, float_format="%.6f")

teams = raw["team"].tolist()
primary_values = z_values.to_numpy()
primary_distances = euclidean_distance_matrix(primary_values)

# Primary-model validation.
assert np.allclose(np.diag(primary_distances), 0.0, atol=1e-12)
assert np.allclose(primary_distances, primary_distances.T, atol=1e-12)
assert np.all(primary_distances >= 0)
assert np.allclose(z_values.mean(), 0.0, atol=1e-12)
assert np.allclose(z_values.std(ddof=0), 1.0, atol=1e-12)
assert standardized[Z_COLUMNS].notna().sum(axis=1).eq(5).all()

pairwise_rows = []
for team_index, team in enumerate(teams):
    for comparison_index, comparison_team in enumerate(teams):
        if team_index == comparison_index:
            continue

        row = {
            "team": team,
            "comparison_team": comparison_team,
            "euclidean_distance": primary_distances[
                team_index, comparison_index
            ],
        }
        for feature_index, feature_name in enumerate(FEATURES):
            difference = (
                primary_values[team_index, feature_index]
                - primary_values[comparison_index, feature_index]
            )
            row[f"{feature_name}_z_difference"] = difference
            row[f"{feature_name}_absolute_z_difference"] = abs(difference)
        pairwise_rows.append(row)

pairwise = pd.DataFrame(pairwise_rows)
assert len(pairwise) == 20 * 19
assert pairwise.groupby("team").size().eq(19).all()
assert pairwise["euclidean_distance"].ge(0).all()
pairwise.to_csv(PAIRWISE_OUTPUT_PATH, index=False, float_format="%.6f")

nearest_five = (
    pairwise.sort_values(
        ["team", "euclidean_distance", "comparison_team"], kind="stable"
    )
    .groupby("team", sort=False)
    .head(5)
    .copy()
)
nearest_five.insert(
    2, "neighbour_rank", nearest_five.groupby("team").cumcount() + 1
)
assert nearest_five.groupby("team").size().eq(5).all()
nearest_five.to_csv(NEIGHBOURS_OUTPUT_PATH, index=False, float_format="%.6f")

# Diagnostic A: min-max scaling. This is not saved as a production fingerprint.
feature_ranges = raw[RAW_COLUMNS].max() - raw[RAW_COLUMNS].min()
assert feature_ranges.gt(0).all()
min_max_values = (
    (raw[RAW_COLUMNS] - raw[RAW_COLUMNS].min()) / feature_ranges
).to_numpy()
min_max_distances = euclidean_distance_matrix(min_max_values)

# Diagnostic B: remove Attacking Width from the already standardized values.
width_index = list(FEATURES).index("attacking_width")
without_width_values = np.delete(primary_values, width_index, axis=1)
without_width_distances = euclidean_distance_matrix(without_width_values)

primary_top_three = ordered_neighbours(primary_distances, teams, 3)
min_max_top_three = ordered_neighbours(min_max_distances, teams, 3)
without_width_top_three = ordered_neighbours(without_width_distances, teams, 3)
team_indices = {team: index for index, team in enumerate(teams)}


def format_neighbours_with_distances(
    team: str, neighbours: list[str], distance_matrix: np.ndarray
) -> str:
    team_index = team_indices[team]
    return " | ".join(
        f"{neighbour} ({distance_matrix[team_index, team_indices[neighbour]]:.4f})"
        for neighbour in neighbours
    )

sensitivity_rows = []
for team in teams:
    primary_set = set(primary_top_three[team])
    min_max_set = set(min_max_top_three[team])
    without_width_set = set(without_width_top_three[team])
    min_max_overlap = len(primary_set & min_max_set)
    without_width_overlap = len(primary_set & without_width_set)
    sensitivity_rows.append(
        {
            "team": team,
            "primary_zscore_top_3": " | ".join(primary_top_three[team]),
            "primary_zscore_top_3_with_distances": format_neighbours_with_distances(
                team, primary_top_three[team], primary_distances
            ),
            "min_max_top_3": " | ".join(min_max_top_three[team]),
            "min_max_top_3_with_distances": format_neighbours_with_distances(
                team, min_max_top_three[team], min_max_distances
            ),
            "min_max_overlap_count": min_max_overlap,
            "min_max_same_set": min_max_overlap == 3,
            "without_width_top_3": " | ".join(without_width_top_three[team]),
            "without_width_top_3_with_distances": format_neighbours_with_distances(
                team, without_width_top_three[team], without_width_distances
            ),
            "without_width_overlap_count": without_width_overlap,
            "without_width_same_set": without_width_overlap == 3,
        }
    )

sensitivity = pd.DataFrame(sensitivity_rows)
sensitivity.to_csv(SENSITIVITY_OUTPUT_PATH, index=False)

print("STANDARDIZATION VALIDATION")
validation = pd.DataFrame(
    {
        "z_mean": z_values.mean(),
        "z_population_std": z_values.std(ddof=0),
    }
)
print(validation.to_string(float_format=lambda value: f"{value:.12f}"))
print(f"Self-distance maximum: {np.diag(primary_distances).max():.12f}")
print(
    "Symmetry maximum absolute error: "
    f"{np.abs(primary_distances - primary_distances.T).max():.12f}"
)
print(f"Minimum distance: {primary_distances.min():.12f}")
print(f"Directed other-team comparisons: {len(pairwise)} (19 per team)")

print("\nPRIMARY TOP 5 NEIGHBOURS")
print(
    nearest_five[
        ["team", "neighbour_rank", "comparison_team", "euclidean_distance"]
    ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
)

print("\nSENSITIVITY SUMMARY")
for label, overlap_column, same_set_column in [
    ("Min-max", "min_max_overlap_count", "min_max_same_set"),
    ("Without Width", "without_width_overlap_count", "without_width_same_set"),
]:
    print(
        f"{label}: exact same top-3 set for "
        f"{int(sensitivity[same_set_column].sum())}/20 teams; "
        f"mean overlap {sensitivity[overlap_column].mean():.2f}/3; "
        f"teams with <=1 shared neighbour: "
        f"{int(sensitivity[overlap_column].le(1).sum())}/20"
    )
    changed = sensitivity.loc[
        sensitivity[overlap_column].le(1),
        ["team", "primary_zscore_top_3", overlap_column],
    ]
    if not changed.empty:
        print(changed.to_string(index=False))
