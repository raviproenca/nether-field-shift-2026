// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Immersive map: Sergipe fills the screen. The user types an address, uses their location or
// clicks the map; the answer floats beside it. The rain risk is computed for that exact point from
// NASA POWER. Live strategy requests use the API when configured; otherwise the panel labels the
// nearest pilot's saved engine run and states when the selected crop history was not applied.
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
import { demoHistoryMatches, recommendationQueryKey, recommendationSource, toRecommendationRequest } from "../recommendationRequest";
import AddressSearch, { type Place } from "./AddressSearch";
import { IMMERSIVE_COPY } from "./copy";
import { fetchLiveRisk } from "./liveRisk";
import { engineNote } from "./engineText";
import ResultPanel, { type RiskState } from "./ResultPanel";
import type { RiskData } from "./RiskChart";

import "../plot.css";
import "./immersive.css";

const REGION = getRegion("sergipe");
const NO_OVERLAYS = Object.fromEntries(GIBS_LAYERS.map((layer) => [layer.id, null])) as Overlays;
const RADIUS_KM = 5;

type Target = { kind: "pilot"; pilot: DemoPilot } | { kind: "point"; place: Place };
type Outcome = { key: string } & ({ ok: true; response: RecommendationResponse; notice: string | null } | { ok: false; message: string });

const initialLang = (): Lang => (window.location.hash === "#pt" ? "pt-BR" : "en");

function inSergipe({ lat, lon }: { lat: number; lon: number }): boolean {
  const [west, south, east, north] = REGION.bbox;
  return lon >= west && lon <= east && lat >= south && lat <= north;
}

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
  const [target, setTarget] = useState<Target | null>(null);
  const [crop, setCrop] = useState<Crop>("maize");
  const [lastCrop, setLastCrop] = useState<Crop | null>(null);
  const [priority, setPriority] = useState<Priority>("water");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [risk, setRisk] = useState<{ id: string; data: RiskData | null } | null>(null);
  const [problem, setProblem] = useState<MapProblem>(null);
  const [panelOpen, setPanelOpen] = useState(true);

  const point = target === null ? null : target.kind === "pilot" ? target.pilot : target.place;
  const placeLabel = target === null ? null : target.kind === "pilot" ? target.pilot.label : target.place.label;
  const outside = point !== null && !inSergipe(point);

  // Resolve an explicitly labeled saved pilot only when the API is not configured.
  const resolved = useMemo(() => {
    if (target === null || outside) return { pilot: null, notice: null };
    if (target.kind === "pilot") return { pilot: target.pilot, notice: null };
    if (!USING_SAMPLE) return { pilot: null, notice: null };
    const { pilot, km } = nearestPilot(target.place);
    return { pilot, notice: copy.nearestPilot(pilot.label, Math.round(km)) };
  }, [target, outside, copy]);

  const pointId = point === null ? null : `${point.lat.toFixed(4)},${point.lon.toFixed(4)}`;
  const request = useMemo(
    () =>
      point === null || outside
        ? null
        : toRecommendationRequest({
            lat: point.lat,
            lon: point.lon,
            radius_km: RADIUS_KM,
            crop,
            previousCrop: lastCrop,
            priority,
            lang,
          }),
    [point, outside, crop, lastCrop, priority, lang],
  );
  const key = request === null ? null : recommendationQueryKey(request);

  useEffect(() => {
    if (key === null || point === null || request === null) return;
    const controller = new AbortController();
    const fromPilot = (pilot: DemoPilot, pointNotice: string | null) =>
      fetchPilotResult(pilot.id, crop, priority, lang, controller.signal).then((response) => {
        const savedPrevious = response.recommendation.plot.previous_crops?.at(-1) ?? null;
        const savedNotice = copy.savedRun(
          pilot.label,
          response.generated_at?.slice(0, 10) ?? copy.dateUnavailable,
          base.crops[response.recommendation.crop] ?? response.recommendation.crop,
          base.priorities[response.recommendation.priority] ?? response.recommendation.priority,
          savedPrevious ? base.crops[savedPrevious] ?? savedPrevious : copy.noPreviousCrop,
          lastCrop ? base.crops[lastCrop] : copy.noPreviousCrop,
          demoHistoryMatches(response.recommendation.plot.previous_crops, lastCrop),
        );
        return { response, notice: [pointNotice, savedNotice].filter(Boolean).join(" ") };
      });
    const live = () =>
      fetchRecommendation(request, controller.signal)
        .then((response) => {
          const { id, name } = response.recommendation.plot;
          return { response, notice: copy.liveNotice(name ?? id ?? `${point.lat.toFixed(3)}, ${point.lon.toFixed(3)}`) };
        });
    const source = recommendationSource(!USING_SAMPLE, resolved.pilot !== null);
    const operation = source === "saved-pilot" && resolved.pilot ? fromPilot(resolved.pilot, resolved.notice) : live();
    operation
      .then(({ response, notice }) => setOutcome({ key, ok: true, response, notice }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setOutcome({ key, ok: false, message: error instanceof RecommendationError ? engineNote(error.message, lang) : base.genericError });
      });
    return () => controller.abort();
  }, [key, point, request, resolved, crop, lastCrop, priority, lang, base, copy]);

  // Rain risk of the exact point: pre-computed for the pilots, computed live from NASA POWER elsewhere.
  const pilotRiskId = target?.kind === "pilot" ? target.pilot.id : null;
  useEffect(() => {
    if (pointId === null || point === null || outside) return;
    const controller = new AbortController();
    const request = pilotRiskId
      ? fetch(`${import.meta.env.BASE_URL}risk/${pilotRiskId}.json`, { signal: controller.signal }).then((response) =>
          response.ok ? (response.json() as Promise<RiskData>) : null,
        )
      : fetchLiveRisk(point.lat, point.lon, controller.signal);
    request
      .then((data) => setRisk({ id: pointId, data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setRisk({ id: pointId, data: null });
      });
    return () => controller.abort();
  }, [pointId, point, pilotRiskId, outside]);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const current = key !== null && outcome !== null && outcome.key === key ? outcome : null;
  const riskState: RiskState = risk !== null && risk.id === pointId ? (risk.data ? { data: risk.data } : "unavailable") : "loading";
  const getPadding = useCallback(() => {
    const wide = window.innerWidth > 900;
    return { top: wide ? 24 : 300, right: wide ? 480 : 24, bottom: wide ? 24 : window.innerHeight * 0.45, left: wide ? 400 : 24 };
  }, []);
  const noop = useCallback(() => undefined, []);
  const choose = (next: Target) => {
    setTarget(next);
    setPanelOpen(true);
  };

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
            onPick={(lat, lon) => choose({ kind: "point", place: { lat, lon, label: `${lat.toFixed(3)}, ${lon.toFixed(3)}` } })}
            marker={point}
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
            <button type="button" className="imm-lang" aria-label={base.languageButtonLabel} onClick={() => setLang(lang === "en" ? "pt-BR" : "en")}>
              {base.languageButton}
            </button>
          </div>
          <AddressSearch lang={lang} copy={copy} onPick={(place) => choose({ kind: "point", place })} />
          <p className="imm-hint">{copy.pickHint}</p>
          <Segmented label={copy.intendedCrop} value={crop} options={CROP_IDS.map((id) => ({ id, label: base.crops[id] }))} onChange={setCrop} />
          <div className="imm-history">
            <label htmlFor="last-crop">{copy.lastCrop}</label>
            <select
              id="last-crop"
              className="imm-select"
              value={lastCrop ?? ""}
              onChange={(event) => setLastCrop(event.target.value ? (event.target.value as Crop) : null)}
            >
              <option value="">{copy.noPreviousCrop}</option>
              {CROP_IDS.map((id) => (
                <option key={id} value={id}>
                  {base.crops[id]}
                </option>
              ))}
            </select>
          </div>
          <Segmented label={copy.priority} value={priority} options={PRIORITY_IDS.map((id) => ({ id, label: base.priorities[id] }))} onChange={setPriority} />
          <div className="imm-examples" role="group" aria-label={copy.examples}>
            <span className="imm-examples-label">{copy.examples}:</span>
            {DEMO_PILOTS.map((pilot) => (
              <button
                key={pilot.id}
                type="button"
                className="imm-example"
                aria-pressed={target?.kind === "pilot" && target.pilot.id === pilot.id}
                onClick={() => choose({ kind: "pilot", pilot })}
              >
                {pilot.label}
              </button>
            ))}
          </div>
        </header>

        <aside className={`imm-panel${panelOpen ? "" : " is-closed"}`} aria-live="polite">
          {target !== null && (
            <button type="button" className="imm-toggle" aria-expanded={panelOpen} onClick={() => setPanelOpen(!panelOpen)}>
              {panelOpen ? copy.close : copy.openPanel}
            </button>
          )}
          {panelOpen && (
            <div className="imm-panel-body">
              {target === null && (
                <div className="empty">
                  <h2 className="empty-title">{copy.emptyTitle}</h2>
                  <p className="muted">{copy.emptyBody}</p>
                </div>
              )}
              {outside && (
                <p className="notice-inline" role="alert">
                  {copy.outsideSergipe}
                </p>
              )}
              {key !== null && current === null && <p className="muted">{base.analysing}</p>}
              {current && !current.ok && (
                <p className="notice-inline" role="alert">
                  {current.message}
                </p>
              )}
              {current?.ok && (
                <ResultPanel
                  recommendation={current.response.recommendation}
                  explanation={current.response.explanation}
                  risk={riskState}
                  place={placeLabel}
                  lang={lang}
                  copy={copy}
                  notice={current.notice}
                />
              )}
            </div>
          )}
        </aside>
      </div>
    </LangContext.Provider>
  );
}
