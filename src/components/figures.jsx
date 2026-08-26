// Cedar Press, collection figures: one renderer per mark kind.
//
// Ported from the app (src/components/grove/collectionFigures.jsx) so the
// standalone page draws the collection with exactly the marks subscribers see
// inside Cedar Grove. The FIGURES map is the module's whole point: the shelf
// picks a renderer by mark kind.

function BarsFigure({ points }) {
  const max = Math.max(...points.map((p) => p.value));
  const width = 320;
  const step = width / points.length;
  const barWidth = Math.min(44, step - 18);
  return (
    <svg viewBox={`0 0 ${width} 130`} role="img" aria-label="Quarterly bars" className="gvc-fig__svg">
      <line x1="4" y1="108" x2={width - 4} y2="108" className="gvc-fig__axis" />
      {points.map((point, index) => {
        const height = Math.round((point.value / max) * 84);
        const x = Math.round(index * step + (step - barWidth) / 2);
        return (
          <g key={point.label}>
            <rect
              x={x}
              y={108 - height}
              width={barWidth}
              height={height}
              rx="3"
              className="gvc-fig__bar"
              style={{ opacity: 0.45 + (0.55 * (index + 1)) / points.length }}
            />
            <text x={x + barWidth / 2} y="124" textAnchor="middle" className="gvc-fig__tick">
              {point.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function LeaderFigure({ points }) {
  const max = Math.max(...points.map((p) => p.value));
  return (
    <svg viewBox="0 0 320 130" role="img" aria-label="Leader comparison" className="gvc-fig__svg">
      {points.map((point, index) => {
        const y = 10 + index * 30;
        const barWidth = Math.round((point.value / max) * 200);
        return (
          <g key={point.label}>
            <text x="0" y={y + 11} className="gvc-fig__ylab">
              {point.label}
            </text>
            <rect
              x="110"
              y={y}
              width={barWidth}
              height="14"
              rx="3"
              className={index === 0 ? "gvc-fig__bar" : "gvc-fig__bar gvc-fig__bar--rest"}
            />
          </g>
        );
      })}
    </svg>
  );
}

function TrendFigure({ points }) {
  const max = Math.max(...points.map((p) => Math.max(p.value, p.compare ?? 0)));
  const x = (index) => 12 + index * ((320 - 24) / (points.length - 1));
  const y = (value) => 104 - Math.round((value / max) * 84);
  const line = points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");
  const compare = points.map((p, i) => `${x(i)},${y(p.compare ?? 0)}`).join(" ");
  const last = points[points.length - 1];
  return (
    <svg viewBox="0 0 320 130" role="img" aria-label="Trend" className="gvc-fig__svg">
      <line x1="4" y1="108" x2="316" y2="108" className="gvc-fig__axis" />
      <polyline points={compare} className="gvc-fig__compare" />
      <polyline points={line} className="gvc-fig__line" />
      <circle cx={x(points.length - 1)} cy={y(last.value)} r="3.5" className="gvc-fig__dot" />
      {points.map((point, index) =>
        index % 2 === 0 ? (
          <text key={point.label} x={x(index)} y="124" textAnchor="middle" className="gvc-fig__tick">
            {point.label}
          </text>
        ) : null,
      )}
    </svg>
  );
}

export const FIGURES = { bars: BarsFigure, leader: LeaderFigure, trend: TrendFigure };
