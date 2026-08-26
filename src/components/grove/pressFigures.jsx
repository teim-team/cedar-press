/* eslint-disable react-refresh/only-export-components -- the PRESS_FIGURES map
   is the module's point: the article picks a renderer by mark kind. */
// REVIEW OWNER: Havala
//
// Cedar Press figures: one renderer per mark.
//
// Wider than Cedar Grove's three marks and for a reason set out in
// features/grove/pressCharts.js: Grove draws generated figures and holds a
// narrow vocabulary to keep a hundred of them legible as a set, while an
// editor building one figure for one article should not have to answer a
// distribution question with a bar chart.
//
// House rules that apply to every mark here. One accent, which is the brand
// teal, and grey for everything the accent is being compared against. No
// gradients inside a mark, no shadows, no 3D. Every axis that carries a
// quantity is labelled, and every mark that hides a choice (a bin width, a
// truncated axis) says so in the notes rather than in the picture.
//
// A figure answers a pointer: hover a bar, a point, a band, a tile or a
// ribbon and a tooltip follows the cursor saying what it is and how much,
// while the mark itself answers in ink. That is where the interactivity
// ends on purpose. Filtering, pivoting and asking a different question of
// the same data is Cedar Grove's job, and the attribution under every
// figure links there.

import { useState } from "react";

/**
 * The tooltip every mark shares. A bare number floating over a bar answers
 * nothing; the tooltip pairs the number with what it belongs to, and
 * follows the cursor so the eye never leaves the mark.
 */
function useTip() {
  const [tip, setTip] = useState(null);
  const move = (text) => (event) => {
    const wrap = event.currentTarget.closest(".pf-wrap");
    if (!wrap) return;
    const box = wrap.getBoundingClientRect();
    // Clamp so a tooltip on an edge mark stays inside the figure.
    const x = Math.max(56, Math.min(box.width - 56, event.clientX - box.left));
    setTip({ x, y: event.clientY - box.top, text });
  };
  return { tip, move, hide: () => setTip(null) };
}

function Frame({ tip, children, values }) {
  return (
    <div className="pf-wrap">
      {children}
      {tip ? (
        <div className="pf__tip" style={{ left: tip.x, top: tip.y }}>{tip.text}</div>
      ) : null}
      {/* The exact values, for readers without a hover: the tooltip lives on
          onMouseMove over a non-focusable SVG, so keyboard, touch and screen
          reader users otherwise get only abbreviated axis labels and cannot
          inspect the numbers they would cite. A visible disclosure rather
          than a screen-reader-only block, because sighted keyboard users
          need the numbers too. */}
      {values?.length ? (
        <details className="pf__data">
          <summary>Exact values</summary>
          <p>{values.join("; ")}.</p>
        </details>
      ) : null}
    </div>
  );
}

/** The per-point value sentences behind a figure, one per drawn mark. */
function valueSentences(points, seriesNames) {
  if (!Array.isArray(points)) return [];
  const names = Array.isArray(seriesNames) && seriesNames.length ? seriesNames : ["value"];
  return points.map((point) =>
    `${point.label}: ${names.map((name) => (names.length > 1 ? `${name} ${point[name]}` : String(point[name]))).join(", ")}`,
  );
}

const TEAL = "var(--dteal)";
const GREY = "var(--line)";

const money = (n) => (n >= 1000 ? `${Math.round(n / 100) / 10}k` : String(n));

// Scale denominator that survives hostile data. All-zero and empty inputs
// otherwise divide by zero and paint NaN into every rect and path, which SVG
// renders as a broken figure rather than an empty one.
const scaleMax = (values) => {
  const finite = values.filter(Number.isFinite);
  const max = finite.length ? Math.max(...finite) : 0;
  return max > 0 ? max : 1;
};

/** Comparison across named things. Zero baseline, always. */
function BarsFigure({ points }) {
  const { tip, move, hide } = useTip();
  const max = scaleMax(points.map((p) => p.value));
  const W = 460;
  const H = 190;
  const pad = { l: 34, r: 8, t: 8, b: 26 };
  const step = (W - pad.l - pad.r) / points.length;
  const barW = Math.max(2, Math.min(46, step - 12));
  return (
    <Frame tip={tip} values={valueSentences(points)}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" className="pf" aria-label="Bar chart">
      <line x1={pad.l} y1={H - pad.b} x2={W - pad.r} y2={H - pad.b} className="pf__axis" />
      <text x="0" y={pad.t + 8} className="pf__ylab">{money(max)}</text>
      <text x="0" y={H - pad.b} className="pf__ylab">0</text>
      {points.map((point, i) => {
        const h = Math.round((point.value / max) * (H - pad.t - pad.b));
        const x = pad.l + i * step + (step - barW) / 2;
        return (
          <g key={point.label} className="pf__hit"
            onMouseMove={move(`${point.label} · ${point.value}`)} onMouseLeave={hide}>
            <rect x={x} y={H - pad.b - h} width={barW} height={h} fill={TEAL} className="pf__bar" />
            <text x={x + barW / 2} y={H - pad.b + 14} textAnchor="middle" className="pf__tick">
              {point.label}
            </text>
          </g>
        );
      })}
    </svg>
    </Frame>
  );
}

/** Change over time. Up to three series on one scale. */
function LineFigure({ points, series }) {
  const { tip, move, hide } = useTip();
  const names = series ?? ["value"];
  const W = 460;
  const H = 190;
  const pad = { l: 34, r: 8, t: 10, b: 26 };
  const max = scaleMax(points.flatMap((p) => names.map((n) => p[n] ?? 0)));
  const x = (i) => pad.l + (i * (W - pad.l - pad.r)) / Math.max(1, points.length - 1);
  const y = (v) => H - pad.b - (v / max) * (H - pad.t - pad.b);
  return (
    <Frame tip={tip} values={valueSentences(points, names)}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" className="pf" aria-label="Line chart">
      <line x1={pad.l} y1={H - pad.b} x2={W - pad.r} y2={H - pad.b} className="pf__axis" />
      <text x="0" y={pad.t + 8} className="pf__ylab">{money(max)}</text>
      <text x="0" y={H - pad.b} className="pf__ylab">0</text>
      {names.map((name, s) => (
        <polyline
          key={name}
          fill="none"
          stroke={s === 0 ? TEAL : GREY}
          strokeWidth={s === 0 ? 2.4 : 1.8}
          // Distinct dash per comparison series: two grey lines with the same
          // dash cannot be told apart, and the vocabulary allows three series.
          strokeDasharray={s === 0 ? undefined : s === 1 ? "4 3" : "1.5 2.5"}
          points={points.map((p, i) => `${x(i)},${y(p[name] ?? 0)}`).join(" ")}
        />
      ))}
      {points.map((p, i) => (
        <text key={p.label} x={x(i)} y={H - pad.b + 14} textAnchor="middle" className="pf__tick">
          {p.label}
        </text>
      ))}
      {/* The dots are the hover targets, drawn after the lines so they sit
          on top. Every series gets them, or only the accent series could be
          questioned. */}
      {names.map((name, s) => (
        points.map((p, i) => (
          <g key={`${name}-${p.label}`} className="pf__hit"
            onMouseMove={move(`${name === "value" ? p.label : `${name} · ${p.label}`} · ${p[name] ?? 0}`)}
            onMouseLeave={hide}>
            <circle cx={x(i)} cy={y(p[name] ?? 0)} r="7" fill="transparent" />
            <circle cx={x(i)} cy={y(p[name] ?? 0)} r="2.4" fill={s === 0 ? TEAL : "var(--muted)"} className="pf__dot" />
          </g>
        ))
      ))}
    </svg>
    </Frame>
  );
}

/** The shape of a distribution. Bins touch, because the axis is continuous. */
function HistogramFigure({ points }) {
  const { tip, move, hide } = useTip();
  const max = scaleMax(points.map((p) => p.value));
  const W = 460;
  const H = 190;
  const pad = { l: 34, r: 8, t: 8, b: 26 };
  const step = (W - pad.l - pad.r) / points.length;
  return (
    <Frame tip={tip} values={valueSentences(points)}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" className="pf" aria-label="Histogram">
      <line x1={pad.l} y1={H - pad.b} x2={W - pad.r} y2={H - pad.b} className="pf__axis" />
      <text x="0" y={pad.t + 8} className="pf__ylab">{money(max)}</text>
      <text x="0" y={H - pad.b} className="pf__ylab">0</text>
      {points.map((point, i) => {
        const h = Math.round((point.value / max) * (H - pad.t - pad.b));
        return (
          <g key={point.label} className="pf__hit"
            onMouseMove={move(`${point.label} · ${point.value}`)} onMouseLeave={hide}>
            <rect
              x={pad.l + i * step}
              y={H - pad.b - h}
              width={Math.max(1, step - 1)}
              height={h}
              fill={TEAL}
              className="pf__bar"
            />
            {i % 2 === 0 ? (
              <text
                x={pad.l + i * step + step / 2}
                y={H - pad.b + 14}
                textAnchor="middle"
                className="pf__tick"
              >
                {point.label}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
    </Frame>
  );
}

/** Composition, and how it moves. Band order is fixed across every bar. */
function StackedFigure({ points, series }) {
  const { tip, move, hide } = useTip();
  const W = 460;
  const H = 190;
  const pad = { l: 34, r: 8, t: 8, b: 34 };
  const totals = points.map((p) => series.reduce((sum, name) => sum + (p[name] ?? 0), 0));
  const max = scaleMax(totals);
  const step = (W - pad.l - pad.r) / points.length;
  const barW = Math.min(52, step - 14);
  // One accent and greys behind it: the first band is the one being claimed
  // about, and the rest are context it is measured against.
  // Floor the alpha: past the fourth band the linear fade otherwise reaches
  // zero and a band occupies stack space while painting nothing.
  const shade = (i) => (i === 0 ? TEAL : `rgba(10, 15, 38, ${Math.max(0.08, 0.34 - i * 0.09)})`);
  return (
    <Frame tip={tip} values={valueSentences(points, series)}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" className="pf" aria-label="Stacked bar chart">
      <line x1={pad.l} y1={H - pad.b} x2={W - pad.r} y2={H - pad.b} className="pf__axis" />
      <text x="0" y={pad.t + 8} className="pf__ylab">{money(max)}</text>
      <text x="0" y={H - pad.b} className="pf__ylab">0</text>
      {points.map((point, i) => {
        const x = pad.l + i * step + (step - barW) / 2;
        let cursor = H - pad.b;
        return (
          <g key={point.label}>
            {series.map((name, s) => {
              const h = Math.round(((point[name] ?? 0) / max) * (H - pad.t - pad.b));
              cursor -= h;
              return (
                <g key={name} className="pf__seg"
                  onMouseMove={move(`${name} · ${point.label} · ${point[name] ?? 0}`)}
                  onMouseLeave={hide}>
                  <rect x={x} y={cursor} width={barW} height={h} fill={shade(s)} />
                </g>
              );
            })}
            <text x={x + barW / 2} y={H - pad.b + 14} textAnchor="middle" className="pf__tick">
              {point.label}
            </text>
          </g>
        );
      })}
      {series.map((name, s) => (
        <g key={name}>
          <rect x={pad.l + s * 110} y={H - 12} width="9" height="9" fill={shade(s)} />
          <text x={pad.l + s * 110 + 13} y={H - 4} className="pf__tick">{name}</text>
        </g>
      ))}
    </svg>
    </Frame>
  );
}

/**
 * A state tile map: one equal square per state, in roughly the country's
 * shape. Deliberately not a land-area choropleth, which would give Alaska
 * forty times the visual weight of Oklahoma on questions where Oklahoma is
 * usually the answer.
 */
const TILE_GRID = Object.freeze({
  AK: [0, 0], ME: [0, 11],
  WI: [1, 6], VT: [1, 10], NH: [1, 11],
  WA: [2, 1], ID: [2, 2], MT: [2, 3], ND: [2, 4], MN: [2, 5], IL: [2, 6], MI: [2, 7], NY: [2, 9], MA: [2, 10],
  OR: [3, 1], NV: [3, 2], WY: [3, 3], SD: [3, 4], IA: [3, 5], IN: [3, 6], OH: [3, 7], PA: [3, 8], NJ: [3, 9], CT: [3, 10], RI: [3, 11],
  CA: [4, 1], UT: [4, 2], CO: [4, 3], NE: [4, 4], MO: [4, 5], KY: [4, 6], WV: [4, 7], VA: [4, 8], MD: [4, 9], DE: [4, 10],
  AZ: [5, 2], NM: [5, 3], KS: [5, 4], AR: [5, 5], TN: [5, 6], NC: [5, 7], SC: [5, 8], DC: [5, 9],
  OK: [6, 4], LA: [6, 5], MS: [6, 6], AL: [6, 7], GA: [6, 8],
  HI: [7, 0], TX: [7, 4], FL: [7, 9],
});

function TilemapFigure({ points }) {
  const { tip, move, hide } = useTip();
  const by = Object.fromEntries(points.map((p) => [p.label, p.value]));
  // Scale only against values that land on a tile: a label outside the grid
  // cannot be drawn, and letting it set the ceiling would mute every state
  // that is actually on the map.
  const max = scaleMax(points.filter((p) => TILE_GRID[p.label]).map((p) => p.value));
  const size = 30;
  const gap = 3;
  const cols = 12;
  const rows = 8;
  const W = cols * (size + gap);
  const H = rows * (size + gap) + 16;
  return (
    <Frame tip={tip} values={valueSentences(points)}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" className="pf" aria-label="State tile map">
      {Object.entries(TILE_GRID).map(([code, [row, col]]) => {
        const value = by[code];
        // Zero is data. A state reporting nothing and a state absent from the
        // dataset are different facts and must not paint the same tile.
        const has = Number.isFinite(value);
        const x = col * (size + gap);
        const y = row * (size + gap);
        return (
          <g key={code} className="pf__tilehit"
            onMouseMove={move(has ? `${code} · ${value}` : `${code} · no data`)}
            onMouseLeave={hide}>
            <rect
              x={x}
              y={y}
              width={size}
              height={size}
              fill={has ? TEAL : "transparent"}
              fillOpacity={has ? 0.18 + 0.82 * (value / max) : 1}
              stroke={has ? "none" : GREY}
            />
            <text
              x={x + size / 2}
              y={y + size / 2 + 3.5}
              textAnchor="middle"
              className="pf__tile"
              fill={has && value / max > 0.55 ? "#fff" : "var(--ink-2)"}
            >
              {code}
            </text>
          </g>
        );
      })}
      <text x="0" y={H - 2} className="pf__tick">
        Shaded by value. One tile per state and DC, equal size.
      </text>
    </svg>
    </Frame>
  );
}

/** Where something moves between two sets of things. Width is the quantity. */
function SankeyFigure({ flows }) {
  const { tip, move, hide } = useTip();
  const W = 460;
  const H = 210;
  const padY = 8;
  const left = [...new Set(flows.map((f) => f.from))];
  const right = [...new Set(flows.map((f) => f.to))];
  // Negative flow is not a flow; clamp so one bad value cannot invert the
  // whole geometry (figureProblems refuses such a figure before it ships).
  const magnitude = (v) => (Number.isFinite(v) && v > 0 ? v : 0);
  const total = flows.reduce((sum, f) => sum + magnitude(f.value), 0);
  const span = H - padY * 2;
  const room = Math.max(0, span - 6 * Math.max(left.length, right.length));
  // An all-zero flow set divides by zero and fills the SVG with NaN.
  const scale = (v) => (total > 0 ? (magnitude(v) / total) * room : 0);

  const stack = (names, key) => {
    let y = padY;
    return Object.fromEntries(
      names.map((name) => {
        const size = flows.filter((f) => f[key] === name).reduce((s, f) => s + scale(f.value), 0);
        const at = y;
        y += size + 6;
        return [name, { top: at, size, cursor: at }];
      }),
    );
  };
  const L = stack(left, "from");
  const R = stack(right, "to");

  return (
    <Frame tip={tip} values={(flows || []).map((f) => `${f.from} to ${f.to}: ${f.value}`)}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" className="pf pf--sankey" aria-label="Flow diagram">
      {flows.map((flow, i) => {
        const h = scale(flow.value);
        const a = L[flow.from];
        const b = R[flow.to];
        const y1 = a.cursor;
        const y2 = b.cursor;
        a.cursor += h;
        b.cursor += h;
        const x1 = 118;
        const x2 = W - 118;
        const mid = (x1 + x2) / 2;
        return (
          <g key={`${flow.from}-${flow.to}-${i}`} className="pf__ribbon"
            onMouseMove={move(`${flow.from} → ${flow.to} · ${flow.value}`)}
            onMouseLeave={hide}>
            <path
              d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2} L${x2},${y2 + h} C${mid},${y2 + h} ${mid},${y1 + h} ${x1},${y1 + h} Z`}
              fill={TEAL}
            />
          </g>
        );
      })}
      {left.map((name) => (
        <g key={name}>
          <rect x="112" y={L[name].top} width="6" height={L[name].size} fill={TEAL} />
          <text x="106" y={L[name].top + L[name].size / 2 + 3.5} textAnchor="end" className="pf__node">
            {name}
          </text>
        </g>
      ))}
      {right.map((name) => (
        <g key={name}>
          <rect x={W - 118} y={R[name].top} width="6" height={R[name].size} fill={TEAL} />
          <text x={W - 106} y={R[name].top + R[name].size / 2 + 3.5} className="pf__node">
            {name}
          </text>
        </g>
      ))}
    </svg>
    </Frame>
  );
}

export const PRESS_FIGURES = {
  bars: BarsFigure,
  line: LineFigure,
  histogram: HistogramFigure,
  stacked: StackedFigure,
  tilemap: TilemapFigure,
  sankey: SankeyFigure,
};
