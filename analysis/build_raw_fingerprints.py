from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data/processed"
OUTPUT_PATH = (
    PROCESSED_DIR / "premier_league_2015_16_raw_tactical_fingerprints.csv"
)

FEATURE_SOURCES = {
    "attacking_territory_share_pct": (
        PROCESSED_DIR / "attacking_territory_share_2015_16.csv",
        "attacking_territory_share_pct",
    ),
    "pass_verticality": (
        PROCESSED_DIR / "pass_verticality_2015_16.csv",
        "pass_verticality",
    ),
    "high_zone_pressures_per_100_opposition_passes": (
        PROCESSED_DIR
        / "high_zone_pressures_per_100_opposition_passes_2015_16.csv",
        "high_zone_pressures_per_100_opposition_passes",
    ),
    "mean_final_third_destination_width": (
        PROCESSED_DIR / "mean_final_third_destination_width_2015_16.csv",
        "mean_final_third_destination_width",
    ),
    "from_counter_possession_rate": (
        PROCESSED_DIR / "from_counter_possession_rate_2015_16.csv",
        "from_counter_possession_rate",
    ),
}

feature_tables = {}
reference_teams = None

for output_column, (source_path, source_column) in FEATURE_SOURCES.items():
    source = pd.read_csv(source_path)
    required_columns = {"team", source_column}
    assert required_columns.issubset(source.columns)
    assert len(source) == 20
    assert source["team"].nunique() == 20
    assert not source[["team", source_column]].isna().any().any()

    teams = set(source["team"])
    if reference_teams is None:
        reference_teams = teams
    else:
        assert teams == reference_teams

    feature_tables[output_column] = source.loc[:, ["team", source_column]].rename(
        columns={source_column: output_column}
    )

combined = None
for table in feature_tables.values():
    combined = (
        table
        if combined is None
        else combined.merge(table, on="team", how="inner", validate="one_to_one")
    )

combined = combined.sort_values("team").reset_index(drop=True)
metric_columns = list(FEATURE_SOURCES)

assert len(combined) == 20
assert combined["team"].nunique() == 20
assert set(combined["team"]) == reference_teams
assert not combined.isna().any().any()
assert combined.loc[:, metric_columns].apply(pd.api.types.is_numeric_dtype).all()

combined.to_csv(OUTPUT_PATH, index=False, float_format="%.4f")

summary = pd.DataFrame(
    {
        "minimum": combined[metric_columns].min(),
        "maximum": combined[metric_columns].max(),
        "mean": combined[metric_columns].mean(),
        "standard_deviation": combined[metric_columns].std(ddof=0),
    }
)
summary["range"] = summary["maximum"] - summary["minimum"]

correlations = combined[metric_columns].corr(method="pearson")
z_scores = (
    combined[metric_columns] - combined[metric_columns].mean()
) / combined[metric_columns].std(ddof=0)
outlier_rows = []
for metric in metric_columns:
    for row_index in z_scores.index[z_scores[metric].abs().ge(2)]:
        outlier_rows.append(
            {
                "team": combined.loc[row_index, "team"],
                "metric": metric,
                "raw_value": combined.loc[row_index, metric],
                "z_score": z_scores.loc[row_index, metric],
            }
        )
outliers = pd.DataFrame(outlier_rows)

print("COMBINED RAW FINGERPRINTS")
print(combined.to_string(index=False))
print("\nFEATURE SUMMARY (population standard deviation, ddof=0)")
print(summary.to_string(float_format=lambda value: f"{value:.4f}"))
print("\nPEARSON CORRELATION MATRIX")
print(correlations.to_string(float_format=lambda value: f"{value:.3f}"))
print("\nPOTENTIAL UNIVARIATE OUTLIERS (absolute z-score >= 2)")
print(
    "None"
    if outliers.empty
    else outliers.to_string(
        index=False,
        formatters={
            "raw_value": "{:.4f}".format,
            "z_score": "{:.2f}".format,
        },
    )
)
