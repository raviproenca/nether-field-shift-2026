// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import type { Metric } from "./labels";
import {
  STRATEGY_TITLES,
  TRADE_OFF_LABELS,
  cropLabel,
  diagnosisMetrics,
  formatDay,
  formatNumber,
  projectionMetrics,
} from "./labels";
import { ClimateCharts, WaterDemandChart } from "./Charts";
import type { Recommendation, SourceAttribution, Strategy } from "./types";

function SourceLink({ source }: { source: SourceAttribution | undefined }) {
  if (!source) {
    return <span className="source">Derived by the engine</span>;
  }
  return (
    <a className="source" href={source.url} target="_blank" rel="noopener noreferrer">
      {source.source.toUpperCase()}
      {source.nasa ? " (NASA)" : ""}
    </a>
  );
}

function MetricTable({ caption, metrics, sources }: { caption: string; metrics: Metric[]; sources: SourceAttribution[] }) {
  return (
    <table className="metrics">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th scope="col">Measure</th>
          <th scope="col">Value</th>
          <th scope="col">Source</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((metric) => (
          <tr key={metric.label}>
            <th scope="row">{metric.label}</th>
            <td className="num">{formatNumber(metric.value, metric.unit)}</td>
            <td>
              <SourceLink source={sources.find((source) => source.source === metric.sourceId)} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StrategyCard({ strategy }: { strategy: Strategy }) {
  return (
    <article className="strategy" aria-labelledby={`strategy-${strategy.kind}`}>
      <p className="strategy-rank">#{strategy.rank}</p>
      <h3 id={`strategy-${strategy.kind}`} className="strategy-title">
        {STRATEGY_TITLES[strategy.kind] ?? strategy.title}
      </h3>
      <p className="strategy-crops">{strategy.crops.map(cropLabel).join(" + ")}</p>
      <h4 className="strategy-heading">Trade-offs</h4>
      <ul>
        {strategy.trade_offs.map((tradeOff) => (
          <li key={tradeOff}>{TRADE_OFF_LABELS[tradeOff] ?? tradeOff}</li>
        ))}
        <li>{strategy.breaks_pest_cycle ? "Breaks the pest cycle" : "Does not break the pest cycle"}</li>
        <li className="num">Water demand: {formatNumber(strategy.water_demand_mm, "mm")}</li>
      </ul>
      <h4 className="strategy-heading">Planting dates</h4>
      <ul>
        {strategy.planting_schedule.map((item) => (
          <li key={item.crop}>
            <span className="strong">{cropLabel(item.crop)}</span>: {formatDay(item.planting_start)} to{" "}
            {formatDay(item.planting_end)}, <span className="num">{item.cycle_days} days</span> to harvest
          </li>
        ))}
      </ul>
      <h4 className="strategy-heading">What to do</h4>
      <ul>
        {strategy.actions.map((action) => (
          <li key={action.code}>
            {action.summary} <span className="muted">{action.evidence}</span>
          </li>
        ))}
      </ul>
      <p className="muted">{strategy.pest_cycle_note}</p>
    </article>
  );
}

export default function PlotView({ recommendation, explanation }: { recommendation: Recommendation; explanation: string }) {
  const { diagnosis, projection, strategies } = recommendation;
  const ranked = [...strategies].sort((a, b) => a.rank - b.rank);
  return (
    <div className="plot-view">
      <section aria-labelledby="strategies-heading">
        <h2 id="strategies-heading" className="section-title">
          Three strategies, side by side
        </h2>
        <div className="strategies">
          {ranked.map((strategy) => (
            <StrategyCard key={strategy.kind} strategy={strategy} />
          ))}
        </div>
        <div className="note">
          <p>{recommendation.uncertainty_note}</p>
          <p>{recommendation.validation_note}</p>
        </div>
        <h3 className="strategy-heading">Summary</h3>
        <pre className="explanation">{explanation}</pre>
      </section>
      <section aria-labelledby="evidence-heading">
        <h2 id="evidence-heading" className="section-title">
          Evidence
        </h2>
        <ClimateCharts diagnosis={diagnosis} projection={projection} />
        <WaterDemandChart strategies={ranked} />
        <MetricTable caption="Diagnosis: what satellites observed" metrics={diagnosisMetrics(diagnosis)} sources={diagnosis.sources} />
        {projection.available && (
          <MetricTable caption="Projection: next 15 days" metrics={projectionMetrics(projection)} sources={projection.sources} />
        )}
      </section>
    </div>
  );
}
