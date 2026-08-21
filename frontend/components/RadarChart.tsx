import type { Feature } from "@/lib/types";

type Series = {
  label: string;
  color: string;
  features: Feature[];
};

type RadarChartProps = {
  series: Series[];
};

const SIZE = 440;
const CENTRE = SIZE / 2;
const RADIUS = 138;

function point(index: number, value: number, total: number, radius = RADIUS) {
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / total;
  const scaledRadius = radius * (value / 100);
  return {
    x: CENTRE + Math.cos(angle) * scaledRadius,
    y: CENTRE + Math.sin(angle) * scaledRadius,
  };
}

function polygon(values: number[]) {
  return values
    .map((value, index) => {
      const position = point(index, value, values.length);
      return `${position.x},${position.y}`;
    })
    .join(" ");
}

export function RadarChart({ series }: RadarChartProps) {
  const features = series[0]?.features ?? [];
  const levels = [20, 40, 60, 80, 100];

  return (
    <div className="radar-wrap">
      <svg
        className="radar"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={`League-relative tactical fingerprint for ${series.map((item) => item.label).join(" and ")}`}
      >
        {levels.map((level) => (
          <polygon
            key={level}
            points={polygon(features.map(() => level))}
            className="radar-grid"
          />
        ))}
        {features.map((feature, index) => {
          const outer = point(index, 100, features.length);
          const label = point(index, 100, features.length, 185);
          return (
            <g key={feature.key}>
              <line
                x1={CENTRE}
                y1={CENTRE}
                x2={outer.x}
                y2={outer.y}
                className="radar-axis"
              />
              <text
                x={label.x}
                y={label.y}
                textAnchor="middle"
                dominantBaseline="middle"
                className="radar-label"
              >
                {feature.label === "Counterattacking Tendency"
                  ? "Counter tendency"
                  : feature.label}
              </text>
            </g>
          );
        })}
        {series.map((item) => (
          <g key={item.label}>
            <polygon
              points={polygon(item.features.map((feature) => feature.display_value))}
              fill={item.color}
              fillOpacity="0.18"
              stroke={item.color}
              strokeWidth="3"
              strokeLinejoin="round"
            />
            {item.features.map((feature, index) => {
              const position = point(index, feature.display_value, features.length);
              return (
                <circle
                  key={feature.key}
                  cx={position.x}
                  cy={position.y}
                  r="4.5"
                  fill={item.color}
                  stroke="#07110e"
                  strokeWidth="2"
                />
              );
            })}
          </g>
        ))}
      </svg>
      {series.length > 1 && (
        <div className="radar-legend">
          {series.map((item) => (
            <span key={item.label}>
              <i style={{ background: item.color }} /> {item.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
