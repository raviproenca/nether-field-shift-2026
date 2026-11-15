// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import { useCallback, useEffect, useState } from "react";
import BaseMap, { type MapProblem, type Overlays } from "../BaseMap";
import { GIBS_LAYERS } from "../gibs/layers";
import { getRegion } from "../regions";
import { RecommendationError, USING_SAMPLE, fetchDemo, fetchRecommendation } from "./api";
import { DEMO_PILOTS, type DemoPilot } from "./demo";
import { CROPS, PRIORITIES } from "./labels";
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
  const [crop, setCrop] = useState<Crop>("maize");
  const [priority, setPriority] = useState<Priority>("water");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [problem, setProblem] = useState<MapProblem>(null);

  // The outcome is tied to the inputs that produced it, so a change shows "loading" without a state reset.
  const key = demo ? `demo:${demo.id}` : point ? `${point.lat},${point.lon},${crop},${priority}` : null;

  useEffect(() => {
    if (key === null) {
      return;
    }
    const controller = new AbortController();
    const request = demo
      ? fetchDemo(demo.id, controller.signal)
      : fetchRecommendation({ ...point!, radius_km: RADIUS_KM, crop, priority, lang: "en" }, controller.signal);
    request
      .then((response) => setOutcome({ key, ok: true, response }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setOutcome({
          key,
          ok: false,
          message: error instanceof RecommendationError ? error.message : "Something went wrong. Try again.",
        });
      });
    return () => controller.abort();
  }, [key, point, demo, crop, priority]);

  const current = outcome !== null && outcome.key === key ? outcome : null;

  const getPadding = useCallback(() => NO_PADDING, []);
  const noop = useCallback(() => undefined, []);

  return (
    <div className="plot-app">
      <header className="plot-header">
        <h1 className="panel-title">Field Shift: planting decision</h1>
        <p className="muted">Click a point on the map, choose a crop and a priority, and compare three strategies.</p>
        <div className="demo-bar" role="group" aria-label="Demo pilots">
          <span className="muted">Quick demo:</span>
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
            <span>Crop</span>
            <select value={crop} onChange={(event) => setCrop(event.target.value as Crop)}>
              {CROPS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Priority</span>
            <select value={priority} onChange={(event) => setPriority(event.target.value as Priority)}>
              {PRIORITIES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {(demo ?? point) && (
          <p className="num muted">
            Selected point: {(demo ?? point)!.lat.toFixed(3)}, {(demo ?? point)!.lon.toFixed(3)}
          </p>
        )}
        {USING_SAMPLE && !demo && (
          <p className="notice-inline">
            Sample result: no analysis service is configured, so this shows one saved engine run (Itabaiana, maize) for any point.
          </p>
        )}
      </header>
      <div className="plot-map" aria-label="Map of Sergipe. Click to choose the plot.">
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
            {problem === "tiles" ? "Map tiles couldn't load. Check your connection, then reload." : "This browser can't draw the map."}
          </p>
        )}
      </div>
      <main className="plot-results" aria-live="polite">
        {key === null && <p className="muted">No plot selected yet.</p>}
        {key !== null && current === null && <p>Analysing the plot…</p>}
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
  );
}
