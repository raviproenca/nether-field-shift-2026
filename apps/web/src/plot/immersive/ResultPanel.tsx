// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// The floating result panel: the answer first, then the other strategies, the seasonal risk and the details.
import { COPY, type Lang, formatDay } from "../i18n";
import PlotView from "../PlotView";
import type { Recommendation, Strategy } from "../types";
import type { ImmersiveCopy } from "./copy";
import { actionEvidence, engineNote } from "./engineText";
import RiskChart, { type RiskData } from "./RiskChart";

const BACKTEST_URL = "https://github.com/raviproenca/nether-field-shift-2026/pull/96";
const SEVERE_DEFICIT_MM = -150; // thresholds.yaml water_balance.severe_deficit_mm

const fmt = (value: number | null | undefined, lang: Lang, digits = 0): string =>
  value === null || value === undefined ? "—" : value.toLocaleString(lang, { maximumFractionDigits: digits, minimumFractionDigits: digits });

function headline(top: Strategy, recommendation: Recommendation, lang: Lang, copy: ImmersiveCopy): string[] {
  const base = COPY[lang];
  const crops = top.crops.map((crop) => base.crops[crop]?.toLowerCase() ?? crop).join(" + ");
  const schedule = top.planting_schedule[0];
  const codes = new Set(top.actions.map((action) => action.code));
  const lines: string[] = [];
  if (codes.has("delay_if_dry")) {
    lines.push(copy.waitBecause(fmt(recommendation.diagnosis.water_balance_mm, lang), fmt(SEVERE_DEFICIT_MM, lang)));
  }
  if (schedule) {
    const plant = copy.plantBetween(crops, formatDay(schedule.planting_start, lang), formatDay(schedule.planting_end, lang));
    lines.push(`${plant}${codes.has("plant_on_contour") ? copy.onContour : ""}.${codes.has("protect_soil") ? copy.keepCovered : ""}`);
  }
  return lines;
}

function Figure({ label, value, unit, note }: { label: string; value: string; unit: string; note?: string }) {
  return (
    <div className="figure">
      <span className="figure-label">{label}</span>
      <span className="figure-value num">
        {value}
        <span className="figure-unit"> {unit}</span>
      </span>
      {note && <span className="figure-note">{note}</span>}
    </div>
  );
}

function Alternative({ strategy, best, lang, copy }: { strategy: Strategy; best: number; lang: Lang; copy: ImmersiveCopy }) {
  const base = COPY[lang];
  return (
    <details className="alt">
      <summary>
        <span className="alt-rank num">#{strategy.rank}</span>
        <span className="alt-main">
          <span className="alt-title">{base.strategyTitles[strategy.kind] ?? strategy.title}</span>
          <span className="alt-crops">{strategy.crops.map((crop) => base.crops[crop] ?? crop).join(" + ")}</span>
        </span>
        <span className="alt-score" aria-label={`${copy.score} ${fmt(strategy.score, lang, 2)}`}>
          <span className="alt-score-bar" style={{ transform: `scaleX(${best ? strategy.score / best : 0})` }} />
        </span>
      </summary>
      <ul className="alt-actions">
        {strategy.actions.map((action) => (
          <li key={action.code}>
            <strong>{base.actions[action.code] ?? action.summary}</strong> <span className="muted">{actionEvidence(action, lang)}</span>
          </li>
        ))}
        <li className="muted">{engineNote(strategy.pest_cycle_note, lang)}</li>
      </ul>
    </details>
  );
}

export default function ResultPanel({
  recommendation,
  explanation,
  risk,
  lang,
  copy,
  notice,
}: {
  recommendation: Recommendation;
  explanation: string;
  risk: RiskData | null;
  lang: Lang;
  copy: ImmersiveCopy;
  notice: string | null;
}) {
  const base = COPY[lang];
  const ranked = [...recommendation.strategies].sort((a, b) => a.rank - b.rank);
  const [top, ...others] = ranked;
  const { diagnosis, projection } = recommendation;
  return (
    <div className="result">
      {notice && <p className="notice-inline">{notice}</p>}
      <section className="answer" aria-labelledby="answer-heading">
        <p className="answer-kicker" id="answer-heading">
          {copy.recommendation} · {base.crops[recommendation.crop]} · {base.priorities[recommendation.priority]}
        </p>
        <h2 className="answer-title">{base.strategyTitles[top.kind] ?? top.title}</h2>
        <p className="answer-crops">{top.crops.map((crop) => base.crops[crop] ?? crop).join(" + ")}</p>
        {headline(top, recommendation, lang, copy).map((line) => (
          <p key={line} className="answer-line">
            {line}
          </p>
        ))}
        <p className="confidence">
          {copy.confidence}{" "}
          <a href={BACKTEST_URL} target="_blank" rel="noopener noreferrer">
            {copy.backtestLink}
          </a>
        </p>
      </section>

      <div className="figures">
        <Figure label={copy.balance} value={fmt(diagnosis.water_balance_mm, lang)} unit="mm" note={`${formatDay(diagnosis.period_start, lang)} – ${formatDay(diagnosis.period_end, lang)}`} />
        <Figure label={copy.slope} value={fmt(diagnosis.slope_mean_pct, lang, 1)} unit="%" note="NASADEM" />
        <Figure
          label={copy.forecastRain}
          value={projection.available ? fmt(projection.rain_total_mm, lang) : "—"}
          unit="mm"
          note={copy.next15}
        />
      </div>

      <section aria-labelledby="alt-heading">
        <h3 id="alt-heading" className="panel-heading">
          {copy.alternatives}
        </h3>
        <div className="alts">
          {others.map((strategy) => (
            <Alternative key={strategy.kind} strategy={strategy} best={top.score} lang={lang} copy={copy} />
          ))}
        </div>
      </section>

      {risk && (
        <section aria-labelledby="risk-heading">
          <h3 id="risk-heading" className="panel-heading">
            {copy.risk}
          </h3>
          <RiskChart data={risk} crop={recommendation.crop} cropLabel={base.crops[recommendation.crop]?.toLowerCase() ?? recommendation.crop} copy={copy} />
        </section>
      )}

      <p className="note-line muted small">{engineNote(recommendation.validation_note, lang)}</p>

      <details className="more">
        <summary>{copy.details}</summary>
        <PlotView recommendation={recommendation} explanation={explanation} />
      </details>
    </div>
  );
}
