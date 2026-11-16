// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import { formatDay } from "./i18n";
import { useCopy, useLang } from "./LangContext";
import type { Metric } from "./labels";
import { diagnosisMetrics, formatNumber, projectionMetrics } from "./labels";
import { ClimateCharts, WaterDemandChart } from "./Charts";
import type { Recommendation, SourceAttribution, Strategy } from "./types";
import { hasSupportedPreviousCrop } from "./recommendationRequest";
import { engineNote } from "./immersive/engineText";

function SourceLink({ source }: { source: SourceAttribution | undefined }) {
  const copy = useCopy();
  if (!source) {
    return <span className="source">{copy.derivedBySystem}</span>;
  }
  return (
    <a className="source" href={source.url} target="_blank" rel="noopener noreferrer">
      {source.source.toUpperCase()}
      {source.nasa ? " (NASA)" : ""}
    </a>
  );
}

function MetricTable({ caption, metrics, sources }: { caption: string; metrics: Metric[]; sources: SourceAttribution[] }) {
  const copy = useCopy();
  return (
    <table className="metrics">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th scope="col">{copy.measure}</th>
          <th scope="col">{copy.value}</th>
          <th scope="col">{copy.source}</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((metric) => (
          <tr key={metric.label}>
            <th scope="row">{metric.label}</th>
            <td className="num">{formatNumber(metric.value, metric.unit, copy.noData)}</td>
            <td>
              <SourceLink source={sources.find((source) => source.source === metric.sourceId)} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StrategyCard({ strategy, historyKnown }: { strategy: Strategy; historyKnown: boolean }) {
  const copy = useCopy();
  const lang = useLang();
  return (
    <article className="strategy" aria-labelledby={`strategy-${strategy.kind}`}>
      <p className="strategy-rank">#{strategy.rank}</p>
      <h3 id={`strategy-${strategy.kind}`} className="strategy-title">
        {copy.strategyTitles[strategy.kind] ?? strategy.title}
      </h3>
      <p className="strategy-crops">{strategy.crops.map((crop) => copy.crops[crop] ?? crop).join(" + ")}</p>
      <p className="strategy-score">
        {copy.score}: {strategy.score.toLocaleString(lang, { maximumFractionDigits: 3 })}
      </p>
      <h4 className="strategy-heading">{copy.tradeOffs}</h4>
      <ul>
        {strategy.trade_offs.map((tradeOff) => (
          <li key={tradeOff}>{copy.tradeOffLabels[tradeOff] ?? tradeOff}</li>
        ))}
        <li>{historyKnown ? (strategy.breaks_pest_cycle ? copy.pestBroken : copy.pestNotBroken) : copy.pestNotAssessed}</li>
        <li className="num">
          {copy.waterDemand}: {formatNumber(strategy.water_demand_mm, copy.units.mm, copy.noData)}
        </li>
      </ul>
      <h4 className="strategy-heading">{copy.plantingDates}</h4>
      <ul>
        {strategy.planting_schedule.map((item) => (
          <li key={item.crop}>
            <span className="strong">{copy.crops[item.crop] ?? item.crop}</span>: {formatDay(item.planting_start, lang)}{" "}
            {copy.to} {formatDay(item.planting_end, lang)}, <span className="num">{copy.toHarvest(item.cycle_days)}</span>
          </li>
        ))}
      </ul>
      <h4 className="strategy-heading">{copy.whatToDo}</h4>
      <ul>
        {strategy.actions.map((action) => (
          <li key={action.code}>
            {copy.actions[action.code] ?? action.summary} <span className="muted">{action.evidence}</span>
          </li>
        ))}
      </ul>
      {historyKnown && <p className="muted">{engineNote(strategy.pest_cycle_note, lang)}</p>}
    </article>
  );
}

export default function PlotView({ recommendation, explanation }: { recommendation: Recommendation; explanation: string }) {
  const copy = useCopy();
  const lang = useLang();
  const { diagnosis, projection, strategies } = recommendation;
  const ranked = [...strategies].sort((a, b) => a.rank - b.rank);
  const lastCrop = recommendation.plot.previous_crops?.at(-1);
  const historyKnown = hasSupportedPreviousCrop(recommendation.plot.previous_crops);
  return (
    <div className="plot-view">
      <section aria-labelledby="strategies-heading">
        <h2 id="strategies-heading" className="section-title">
          {copy.strategiesHeading}
        </h2>
        <p className="muted">
          {copy.cropHistory(lastCrop ? copy.crops[lastCrop] ?? lastCrop : copy.noPreviousCrop, copy.crops[recommendation.crop] ?? recommendation.crop)}
        </p>
        <p className="muted small">{copy.scoreBasis}</p>
        <div className="strategies">
          {ranked.map((strategy) => (
            <StrategyCard key={strategy.kind} strategy={strategy} historyKnown={historyKnown} />
          ))}
        </div>
        <div className="note">
          <p>{engineNote(recommendation.uncertainty_note, lang)}</p>
          <p>{engineNote(recommendation.validation_note, lang)}</p>
        </div>
        <h3 className="strategy-heading">{copy.summary}</h3>
        <pre className="explanation">{engineNote(explanation, lang)}</pre>
      </section>
      <section aria-labelledby="evidence-heading">
        <h2 id="evidence-heading" className="section-title">
          {copy.evidenceHeading}
        </h2>
        <ClimateCharts diagnosis={diagnosis} projection={projection} />
        <WaterDemandChart strategies={ranked} />
        <MetricTable caption={copy.diagnosisTable} metrics={diagnosisMetrics(diagnosis, copy)} sources={diagnosis.sources} />
        {projection.available && (
          <MetricTable caption={copy.projectionTable} metrics={projectionMetrics(projection, copy)} sources={projection.sources} />
        )}
      </section>
    </div>
  );
}
