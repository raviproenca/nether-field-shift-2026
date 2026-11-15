// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Immersive map: Sergipe fills the screen; pick a pilot or a point, and the answer floats beside it.
// Changing the crop or the priority answers instantly from the pre-computed engine runs of the pilots;
// any other point goes to the API when VITE_API_URL is set.
import { useCallback, useEffect, useMemo, useState } from "react";
import BaseMap, { type MapProblem, type Overlays } from "../../BaseMap";
import { GIBS_LAYERS } from "../../gibs/layers";
import { getRegion } from "../../regions";
import { RecommendationError, USING_SAMPLE, fetchPilotResult, fetchRecommendation } from "../api";
import { DEMO_PILOTS, type DemoPilot } from "../demo";
import { COPY, type Lang } from "../i18n";
import { LangContext } from "../LangContext";
import { CROP_IDS, PRIORITY_IDS } from "../labels";
import type { Crop, Priority, RecommendationResponse } from "../types";
import { IMMERSIVE_COPY } from "./copy";
import ResultPanel from "./ResultPanel";
import type { RiskData } from "./RiskChart";

import "../plot.css";
import "./immersive.css";

const REGION = getRegion("sergipe");
const NO_OVERLAYS = Object.fromEntries(GIBS_LAYERS.map((layer) => [layer.id, null])) as Overlays;
const RADIUS_KM = 5;

type Target = { kind: "pilot"; pilot: DemoPilot } | { kind: "point"; lat: number; lon: number };
type Outcome = { key: string } & ({ ok: true; response: RecommendationResponse } | { ok: false; message: string });

const initialLang = (): Lang => (window.location.hash === "#pt" ? "pt-BR" : "en");

function distanceKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLon = (b.lon - a.lon) * rad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

function nearestPilot(point: { lat: number; lon: number }): { pilot: DemoPilot; km: number } {
  return DEMO_PILOTS.map((pilot) => ({ pilot, km: distanceKm(point, pilot) })).sort((a, b) => a.km - b.km)[0];
}

function Segmented<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { id: T; label: string }[]; onChange: (id: T) => void }) {
  return (
    <fieldset className="seg">
      <legend>{label}</legend>
      <div className="seg-row">
        {options.map((option) => (
          <label key={option.id} className="seg-option">
            <input type="radio" name={label} value={option.id} checked={value === option.id} onChange={() => onChange(option.id)} />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function ImmersiveApp() {
  const [lang, setLang] = useState<Lang>(initialLang);
  const copy = IMMERSIVE_COPY[lang];
  const base = COPY[lang];
  const [target, setTarget] = useState<Target>({ kind: "pilot", pilot: DEMO_PILOTS[1] });
  const [crop, setCrop] = useState<Crop>("maize");
  const [priority, setPriority] = useState<Priority>("water");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [risk, setRisk] = useState<{ id: string; data: RiskData | null } | null>(null);
  const [problem, setProblem] = useState<MapProblem>(null);
  const [panelOpen, setPanelOpen] = useState(true);

  // Without the API, a clicked point is answered by the nearest pilot, and the panel says so.
  const resolved = useMemo(() => {
    if (target.kind === "pilot") return { pilot: target.pilot, notice: null };
    if (!USING_SAMPLE) return { pilot: null, notice: null };
    const { pilot, km } = nearestPilot(target);
    return { pilot, notice: copy.nearestPilot(pilot.label, Math.round(km)) };
  }, [target, copy]);

  const key = `${target.kind === "pilot" ? target.pilot.id : `${target.lat},${target.lon}`}:${crop}:${priority}:${lang}`;

  useEffect(() => {
    const controller = new AbortController();
    const request = resolved.pilot
      ? fetchPilotResult(resolved.pilot.id, crop, priority, lang, controller.signal)
      : fetchRecommendation(
          { lat: (target as { lat: number }).lat, lon: (target as { lon: number }).lon, radius_km: RADIUS_KM, crop, priority, lang },
          controller.signal,
        );
    request
      .then((response) => setOutcome({ key, ok: true, response }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setOutcome({ key, ok: false, message: error instanceof RecommendationError ? error.message : base.genericError });
      });
    return () => controller.abort();
  }, [key, resolved, target, crop, priority, lang, base]);

  const riskId = resolved.pilot?.id ?? null;
  useEffect(() => {
    if (!riskId) return;
    const controller = new AbortController();
    fetch(`${import.meta.env.BASE_URL}risk/${riskId}.json`, { signal: controller.signal })
      .then((response) => (response.ok ? (response.json() as Promise<RiskData>) : null))
      .then((data) => setRisk({ id: riskId, data }))
      .catch(() => undefined);
    return () => controller.abort();
  }, [riskId]);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const current = outcome !== null && outcome.key === key ? outcome : null;
  const riskData = risk !== null && risk.id === riskId ? risk.data : null;
  const marker = target.kind === "pilot" ? target.pilot : target;
  const getPadding = useCallback(() => {
    const wide = window.innerWidth > 900;
    return { top: wide ? 200 : 260, right: wide ? 480 : 24, bottom: wide ? 24 : window.innerHeight * 0.5, left: 24 };
  }, []);
  const noop = useCallback(() => undefined, []);

  return (
    <LangContext.Provider value={lang}>
      <div className="imm" lang={lang}>
        <div className="imm-map" aria-label={base.mapLabel}>
          <BaseMap
            region={REGION}
            overlays={NO_OVERLAYS}
            onOverlayError={noop}
            getPadding={getPadding}
            onProblem={setProblem}
            onPick={(lat, lon) => {
              setTarget({ kind: "point", lat, lon });
              setPanelOpen(true);
            }}
            marker={marker}
          />
          {problem && (
            <p className="notice-inline imm-map-notice" role="alert">
              {problem === "tiles" ? base.tilesProblem : base.webglProblem}
            </p>
          )}
        </div>

        <header className="imm-bar">
          <div className="imm-brand">
            <span className="imm-mark" aria-hidden="true" />
            <div>
              <h1 className="imm-title">{copy.product}</h1>
              <p className="imm-tagline">{copy.tagline}</p>
            </div>
            <button
              type="button"
              className="imm-lang"
              aria-label={base.languageButtonLabel}
              onClick={() => setLang(lang === "en" ? "pt-BR" : "en")}
            >
              {base.languageButton}
            </button>
          </div>
          <div className="imm-pilots" role="group" aria-label={copy.pilots}>
            {DEMO_PILOTS.map((pilot) => (
              <button
                key={pilot.id}
                type="button"
                className="imm-pilot"
                aria-pressed={target.kind === "pilot" && target.pilot.id === pilot.id}
                onClick={() => {
                  setTarget({ kind: "pilot", pilot });
                  setPanelOpen(true);
                }}
              >
                {pilot.label}
              </button>
            ))}
          </div>
          <Segmented label={copy.crop} value={crop} options={CROP_IDS.map((id) => ({ id, label: base.crops[id] }))} onChange={setCrop} />
          <Segmented label={copy.priority} value={priority} options={PRIORITY_IDS.map((id) => ({ id, label: base.priorities[id] }))} onChange={setPriority} />
          <p className="imm-hint">{copy.pickHint}</p>
        </header>

        <aside className={`imm-panel${panelOpen ? "" : " is-closed"}`} aria-live="polite">
          <button type="button" className="imm-toggle" aria-expanded={panelOpen} onClick={() => setPanelOpen(!panelOpen)}>
            {panelOpen ? copy.close : copy.openPanel}
          </button>
          {panelOpen && (
            <div className="imm-panel-body">
              {current === null && <p className="muted">{base.analysing}</p>}
              {current && !current.ok && (
                <p className="notice-inline" role="alert">
                  {current.message}
                </p>
              )}
              {current?.ok && (
                <ResultPanel
                  recommendation={current.response.recommendation}
                  explanation={current.response.explanation}
                  risk={riskData}
                  lang={lang}
                  copy={copy}
                  notice={resolved.notice}
                />
              )}
            </div>
          )}
        </aside>
      </div>
    </LangContext.Provider>
  );
}
