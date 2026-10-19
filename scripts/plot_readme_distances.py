"""Plot the five smallest unique pairs in the committed distance CSV."""
import csv
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "data/processed/premier_league_2015_16_pairwise_tactical_distances.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    pairs = {}
    for row in rows:
        a, b = row["team"], row["comparison_team"]
        if a == b:
            continue
        key = tuple(sorted((a, b)))
        value = float(row["euclidean_distance"])
        if key in pairs:
            assert abs(pairs[key] - value) < 1e-6, key
        pairs[key] = value
    chosen = sorted(pairs.items(), key=lambda item: (item[1], item[0]))[:5]
    assert len(pairs) == 190
    assert set(chosen[0][0]) == {"Liverpool", "Tottenham Hotspur"}
    assert round(chosen[0][1], 3) == 0.620
    maximum = max(v for _, v in chosen) * 1.2
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420" role="img" aria-labelledby="title desc">',
           '<title id="title">Five nearest tactical pairs, Premier League 2015/16</title>',
           '<desc id="desc">Unique pair distances from five equally weighted standardized event features. Smaller means closer.</desc>',
           '<rect width="1000" height="420" fill="#fafaf8"/>',
           '<g font-family="Arial, sans-serif" fill="#20252b">',
           '<text x="28" y="36" font-size="23">Nearest pairs in this five-feature season model</text>',
           '<text x="28" y="65" font-size="15">Euclidean distance • smaller is closer • not a probability or a quality ranking</text>']
    for k in range(5):
        value = maximum * k / 4
        x = 430 + value / maximum * 470
        svg += [f'<line x1="{x:.1f}" y1="90" x2="{x:.1f}" y2="355" stroke="#d9dde0"/>',
                f'<text x="{x:.1f}" y="378" text-anchor="middle" font-size="13">{value:.2f}</text>']
    for i, (pair, value) in enumerate(chosen):
        y = 105 + i * 49
        width = value / maximum * 470
        label = escape(" / ".join(pair))
        svg += [f'<text x="28" y="{y+21}" font-size="15">{label}</text>',
                f'<rect x="430" y="{y}" width="{width:.1f}" height="30" fill="#176b75"/>',
                f'<text x="{438+width:.1f}" y="{y+21}" font-size="14">{value:.3f}</text>']
    svg += ['<text x="28" y="408" font-size="13">Source: committed pairwise_tactical_distances.csv • 20 teams / 380 matches</text>', '</g></svg>']
    output = ROOT / "docs/assets/readme-distances.svg"
    output.write_text("\n".join(svg) + "\n")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
