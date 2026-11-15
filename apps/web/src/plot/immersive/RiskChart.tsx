// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Median rain per decendio (April to July) in strong El Niño seasons against the other seasons,
// with the crop's planting window marked. Data: public/risk/<pilot>.json (scripts/build_risk_cache.py).
import { useState } from "react";
import type { ImmersiveCopy } from "./copy";

export interface RiskData {
  decendios: { decendio: number; strong_el_nino_mm: number; other_years_mm: number }[];
  strong_el_nino_years: number[];
  other_years_count: number;
  windows: Record<string, { start: number; end: number }>;
  sources: { name: string; url: string; nasa: boolean }[];
}

const WIDTH = 360;
const HEIGHT = 168;
const PAD = { top: 18, right: 8, bottom: 28, left: 34 };

export default function RiskChart({ data, crop, cropLabel, copy }: { data: RiskData; crop: string; cropLabel: string; copy: ImmersiveCopy }) {
  const [active, setActive] = useState<number | null>(null);
  const rows = data.decendios;
  const max = Math.max(...rows.flatMap((row) => [row.strong_el_nino_mm, row.other_years_mm]), 1);
  const top = Math.ceil(max / 10) * 10;
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotW / rows.length;
  const bar = slot * 0.34;
  const y = (mm: number) => PAD.top + plotH - (mm / top) * plotH;
  const window = data.windows[crop];
  const first = rows[0].decendio;
  const windowX = window ? PAD.left + (window.start - first) * slot : null;
  const windowW = window ? (window.end - window.start + 1) * slot : 0;
  const ticks = [0, top / 2, top];
  const shown = active === null ? null : rows[active];

  return (
    <figure className="risk">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="risk-svg" role="img" aria-label={copy.risk}>
        {windowX !== null && (
          <rect className="risk-window" x={windowX} y={PAD.top} width={windowW} height={plotH} />
        )}
        {ticks.map((tick) => (
          <g key={tick}>
            <line className="risk-grid" x1={PAD.left} x2={WIDTH - PAD.right} y1={y(tick)} y2={y(tick)} />
            <text className="risk-axis" x={PAD.left - 6} y={y(tick) + 4} textAnchor="end">
              {tick}
            </text>
          </g>
        ))}
        {rows.map((row, index) => {
          const x = PAD.left + index * slot + slot / 2;
          return (
            <g
              key={row.decendio}
              className="risk-slot"
              tabIndex={0}
              onMouseEnter={() => setActive(index)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(index)}
              onBlur={() => setActive(null)}
            >
              <rect className="risk-hit" x={x - slot / 2} y={PAD.top} width={slot} height={plotH} />
              <rect className="risk-bar-other" x={x - bar - 1} y={y(row.other_years_mm)} width={bar} height={PAD.top + plotH - y(row.other_years_mm)} />
              <rect className="risk-bar-strong" x={x + 1} y={y(row.strong_el_nino_mm)} width={bar} height={PAD.top + plotH - y(row.strong_el_nino_mm)} />
            </g>
          );
        })}
        {copy.months.map((month, index) => (
          <text key={month} className="risk-axis" x={PAD.left + (index * 3 + 1.5) * slot} y={HEIGHT - 8} textAnchor="middle">
            {month}
          </text>
        ))}
        <text className="risk-axis" x={PAD.left - 6} y={PAD.top - 2} textAnchor="end">
          mm
        </text>
      </svg>
      <p className="risk-readout num" aria-live="polite">
        {shown
          ? `${copy.months[Math.floor((shown.decendio - first) / 3)]} ${((shown.decendio - first) % 3) + 1}/3 · ${copy.otherYears}: ${shown.other_years_mm} mm · ${copy.strongYears}: ${shown.strong_el_nino_mm} mm`
          : " "}
      </p>
      <ul className="risk-legend">
        <li><span className="risk-key risk-key-other" aria-hidden="true" />{copy.otherYears}</li>
        <li><span className="risk-key risk-key-strong" aria-hidden="true" />{copy.strongYears}</li>
        {window && <li><span className="risk-key risk-key-window" aria-hidden="true" />{copy.window(cropLabel)}</li>}
      </ul>
      <figcaption className="muted small">
        {copy.riskCaption(data.strong_el_nino_years.join(", "), data.other_years_count)} {copy.riskNote}
      </figcaption>
    </figure>
  );
}
