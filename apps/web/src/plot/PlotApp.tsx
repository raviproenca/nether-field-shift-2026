// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import { useCallback, useEffect, useState } from "react";
import BaseMap, { type MapProblem, type Overlays } from "../BaseMap";
import { GIBS_LAYERS } from "../gibs/layers";
import { getRegion } from "../regions";
import { RecommendationError, USING_SAMPLE, fetchDemo, fetchRecommendation } from "./api";
import { DEMO_PILOTS, type DemoPilot } from "./demo";
import { COPY, DEFAULT_LANG, type Lang } from "./i18n";
import { LangContext } from "./LangContext";
import { CROP_IDS, PRIORITY_IDS } from "./labels";
import PlotView from "./PlotView";
import type { Crop, Priority, RecommendationResponse } from "./types";

import "./plot.css";

const REGION = getRegion("sergipe");
const NO_OVERLAYS = Object.fromEntries(GIBS_LAYERS.map((layer) => [layer.id, null])) as Overlays;
const NO_PADDING = { top: 24, right: 24, bottom: 24, left: 24 };
const RADIUS_KM = 5;

type Outcome = { key: string } & ({ ok: true; response: RecommendationResponse } | { ok: false; message: string });

export default function PlotApp() {
  const [point, setPoint] = useState<{ lat: number; lon: number } | null>(null);
  const [demo, setDemo] = useState<DemoPilot | null>(null);
  const [lang, setLang] = useState<Lang>(DEFAULT_LANG);
  const copy = COPY[lang];
  const [crop, setCrop] = useState<Crop>("maize");
  const [priority, setPriority] = useState<Priority>("water");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [problem, setProblem] = useState<MapProblem>(null);

  // The outcome is tied to the inputs that produced it, so a change shows "loading" without a state reset.
  const key = demo ? `demo:${demo.id}:${lang}` : point ? `${point.lat},${point.lon},${crop},${priority},${lang}` : null;

  useEffect(() => {
    if (key === null) {
      return;
    }
    const controller = new AbortController();
    const request = demo
      ? fetchDemo(demo.id, lang, controller.signal)
      : fetchRecommendation({ ...point!, radius_km: RADIUS_KM, crop, priority, lang }, controller.signal);
    request
      .then((response) => setOutcome({ key, ok: true, response }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setOutcome({
          key,
          ok: false,
          message: error instanceof RecommendationError ? error.message : COPY[lang].genericError,
        });
      });
    return () => controller.abort();
  }, [key, point, demo, crop, priority, lang]);

  const current = outcome !== null && outcome.key === key ? outcome : null;

  const getPadding = useCallback(() => NO_PADDING, []);
  const noop = useCallback(() => undefined, []);

  return (
    <LangContext.Provider value={lang}>
      <div className="plot-app" lang={lang}>
        <header className="plot-header">
          <div className="plot-title-row">
            <h1 className="panel-title">{copy.title}</h1>
            <button
              type="button"
              className="demo-button"
              lang={lang === "en" ? "pt-BR" : "en"}
              aria-label={copy.languageButtonLabel}
              onClick={() => setLang(lang === "en" ? "pt-BR" : "en")}
            >
              {copy.languageButton}
            </button>
          </div>
          <p className="muted">{copy.intro}</p>
          <div className="demo-bar" role="group" aria-label={copy.demoGroup}>
            <span className="muted">{copy.quickDemo}</span>
            {DEMO_PILOTS.map((pilot) => (
              <button
                key={pilot.id}
                type="button"
                className="demo-button"
                aria-pressed={demo?.id === pilot.id}
                onClick={() => setDemo(pilot)}
              >
                {pilot.label}
              </button>
            ))}
          </div>
          <div className="plot-form">
            <label className="field">
              <span>{copy.crop}</span>
              <select value={crop} onChange={(event) => setCrop(event.target.value as Crop)}>
                {CROP_IDS.map((id) => (
                  <option key={id} value={id}>
                    {copy.crops[id]}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>{copy.priority}</span>
              <select value={priority} onChange={(event) => setPriority(event.target.value as Priority)}>
                {PRIORITY_IDS.map((id) => (
                  <option key={id} value={id}>
                    {copy.priorities[id]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {(demo ?? point) && (
            <p className="num muted">
              {copy.selectedPoint}: {(demo ?? point)!.lat.toFixed(3)}, {(demo ?? point)!.lon.toFixed(3)}
            </p>
          )}
          {USING_SAMPLE && !demo && <p className="notice-inline">{copy.sampleNotice}</p>}
        </header>
        <div className="plot-map" aria-label={copy.mapLabel}>
          <BaseMap
            region={REGION}
            overlays={NO_OVERLAYS}
            onOverlayError={noop}
            getPadding={getPadding}
            onProblem={setProblem}
            onPick={(lat, lon) => {
              setDemo(null);
              setPoint({ lat, lon });
            }}
            marker={demo ?? point}
          />
          {problem && (
            <p className="notice-inline map-notice" role="alert">
              {problem === "tiles" ? copy.tilesProblem : copy.webglProblem}
            </p>
          )}
        </div>
        <main className="plot-results" aria-live="polite">
          {key === null && <p className="muted">{copy.noPlot}</p>}
          {key !== null && current === null && <p>{copy.analysing}</p>}
          {current && !current.ok && (
            <div className="notice-inline" role="alert">
              {current.message}
            </div>
          )}
          {current?.ok && (
            <PlotView recommendation={current.response.recommendation} explanation={current.response.explanation} />
          )}
        </main>
      </div>
    </LangContext.Provider>
  );
}
