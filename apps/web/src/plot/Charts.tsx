// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import type { Diagnosis, Projection, Strategy } from "./types";
import { STRATEGY_TITLES, formatNumber } from "./labels";

interface Bar {
  label: string;
  value: number;
  tone: "observed" | "forecast" | "plain";
}

/** Horizontal bars with a zero axis, so negative water balances read correctly. */
function BarChart({ title, unit, bars, caption }: { title: string; unit: string; bars: Bar[]; caption: string }) {
  const max = Math.max(...bars.map((bar) => Math.abs(bar.value)), 1);
  const hasNegative = bars.some((bar) => bar.value < 0);
  const zero = hasNegative ? 50 : 0;
  const scale = hasNegative ? 50 : 100;
  return (
    <figure className="chart">
      <figcaption className="chart-title">{title}</figcaption>
      <ul className="chart-rows">
        {bars.map((bar) => {
          const width = (Math.abs(bar.value) / max) * scale;
          const left = bar.value < 0 ? zero - width : zero;
          return (
            <li key={bar.label} className="chart-row">
              <span className="chart-label">{bar.label}</span>
              <span className="chart-track" aria-hidden="true">
                <span className={`chart-bar chart-bar-${bar.tone}`} style={{ left: `${left}%`, width: `${width}%` }} />
              </span>
              <span className="chart-value num">{formatNumber(bar.value, unit)}</span>
            </li>
          );
        })}
      </ul>
      <p className="chart-caption">{caption}</p>
    </figure>
  );
}

const present = (value: number | null): value is number => value !== null;

export function ClimateCharts({ diagnosis, projection }: { diagnosis: Diagnosis; projection: Projection }) {
  const compare = (observed: number | null, forecast: number | null): Bar[] => [
    ...(present(observed) ? [{ label: "Observed", value: observed, tone: "observed" as const }] : []),
    ...(projection.available && present(forecast) ? [{ label: "Forecast", value: forecast, tone: "forecast" as const }] : []),
  ];
  const charts = [
    {
      title: "Rain per day",
      unit: "mm/day",
      bars: compare(diagnosis.rain_daily_mean_mm, projection.rain_daily_mean_mm),
    },
    {
      title: "Crop water loss (ET0) per day",
      unit: "mm/day",
      bars: compare(diagnosis.et0_daily_mean_mm, projection.et0_daily_mean_mm),
    },
    {
      title: "Water balance",
      unit: "mm",
      bars: compare(diagnosis.water_balance_mm, projection.water_balance_mm),
    },
  ].filter((chart) => chart.bars.length > 0);
  return (
    <div className="charts">
      {charts.map((chart) => (
        <BarChart
          key={chart.title}
          title={chart.title}
          unit={chart.unit}
          bars={chart.bars}
          caption={`Observed: ${diagnosis.period_start} to ${diagnosis.period_end}.${
            projection.available ? ` Forecast: ${projection.period_start} to ${projection.period_end}.` : ""
          }`}
        />
      ))}
      {!projection.available && <p className="notice-inline">The 15-day forecast is not available right now.</p>}
    </div>
  );
}

export function WaterDemandChart({ strategies }: { strategies: Strategy[] }) {
  return (
    <BarChart
      title="Water demand over the cycle, by strategy"
      unit="mm"
      bars={strategies.map((strategy) => ({
        label: STRATEGY_TITLES[strategy.kind] ?? strategy.title,
        value: strategy.water_demand_mm,
        tone: "plain" as const,
      }))}
      caption="Crop profile water need summed over the planting schedule."
    />
  );
}
