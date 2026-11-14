// AI-assisted: generated with Claude Code, reviewed by Ravi
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import BaseMap, { type MapProblem, type Overlays } from "./BaseMap";
import LayerPanel from "./LayerPanel";
import RegionSelector from "./RegionSelector";
import { canShow, fetchAvailability, pickDefaultDate, type Availability } from "./gibs/availability";
import { formatDate, todayUtc } from "./gibs/dates";
import { GIBS_LAYERS, tilesForDate, type LayerId } from "./gibs/layers";
import { DEFAULT_REGION_ID, formatBbox, getRegion, type RegionId } from "./regions";

const PROBLEM_MESSAGES: Record<Exclude<MapProblem, null>, string> = {
  tiles: "Map tiles couldn't load. Check your connection, then reload.",
  webgl: "This browser can't draw the map because WebGL is off or not supported.",
};

// Breathing room around the framed region, in px (space scale: 4 px steps).
const FRAME_GAP = 24;
// Matches the phone breakpoint in index.css: the panel spans the width and starts collapsed.
const PHONE_QUERY = "(max-width: 640px)";

const LOADING: Record<LayerId, Availability> = Object.fromEntries(
  GIBS_LAYERS.map((layer) => [layer.id, { status: "loading" }]),
) as Record<LayerId, Availability>;

export default function App() {
  const [regionId, setRegionId] = useState<RegionId>(DEFAULT_REGION_ID);
  const [problem, setProblem] = useState<MapProblem>(null);
  const [expanded, setExpanded] = useState(() => !window.matchMedia(PHONE_QUERY).matches);
  const [availability, setAvailability] = useState(LOADING);
  const [date, setDate] = useState<string | null>(null);
  const [active, setActive] = useState<ReadonlySet<LayerId>>(new Set());
  const [failedTiles, setFailedTiles] = useState<ReadonlySet<LayerId>>(new Set());
  const panelRef = useRef<HTMLElement>(null);
  const layersId = useId();
  const region = getRegion(regionId);

  useEffect(() => {
    let current = true;
    Promise.all(GIBS_LAYERS.map(fetchAvailability)).then((results) => {
      if (!current) {
        return;
      }
      const byId = Object.fromEntries(GIBS_LAYERS.map((layer, index) => [layer.id, results[index]]));
      setAvailability(byId as Record<LayerId, Availability>);
      setDate((chosen) => chosen ?? pickDefaultDate(results));
    });
    return () => {
      current = false;
    };
  }, []);

  const minDate = useMemo(() => {
    const firsts = Object.values(availability).flatMap((entry) => (entry.status === "ready" ? [entry.first] : []));
    return firsts.length > 0 ? firsts.sort()[0] : "2000-01-01";
  }, [availability]);

  const overlays = useMemo(
    () =>
      Object.fromEntries(
        GIBS_LAYERS.map((layer) => {
          const shown = date !== null && active.has(layer.id) && canShow(availability[layer.id], date);
          return [layer.id, shown ? tilesForDate(layer, date) : null];
        }),
      ) as Overlays,
    [active, availability, date],
  );

  const changeDate = useCallback((next: string) => {
    setDate(next);
    setFailedTiles(new Set());
  }, []);

  const toggleLayer = useCallback((id: LayerId) => {
    setActive((previous) => {
      const next = new Set(previous);
      if (!next.delete(id)) {
        next.add(id);
      }
      return next;
    });
  }, []);

  const markFailed = useCallback((id: LayerId) => {
    setFailedTiles((previous) => (previous.has(id) ? previous : new Set(previous).add(id)));
  }, []);

  const getPadding = useCallback(() => {
    const panel = panelRef.current?.getBoundingClientRect();
    const padding = { top: FRAME_GAP, right: FRAME_GAP, bottom: FRAME_GAP, left: FRAME_GAP };
    if (!panel) {
      return padding;
    }
    // Phone: the panel spans the top, so frame below it. Wider: it sits on the left, so frame beside it.
    if (window.matchMedia(PHONE_QUERY).matches) {
      return { ...padding, top: panel.bottom + FRAME_GAP };
    }
    return { ...padding, left: panel.right + FRAME_GAP };
  }, []);

  const summary =
    active.size === 0
      ? "No layers on"
      : `${active.size} ${active.size === 1 ? "layer" : "layers"} on${date ? `, ${formatDate(date)}` : ""}`;

  return (
    <div className="app">
      <header ref={panelRef} className="panel">
        <h1 className="panel-title">Nether internal data map</h1>
        <p className="panel-region">
          <span className="panel-region-name">{region.name}</span>
          <span className="panel-meta num">{formatBbox(region.bbox)}</span>
        </p>
        <RegionSelector value={regionId} onChange={setRegionId} />
        {problem && (
          <div className="notice" role="alert">
            <p>{PROBLEM_MESSAGES[problem]}</p>
            {problem === "tiles" && (
              <button type="button" className="text-button" onClick={() => window.location.reload()}>
                Reload
              </button>
            )}
          </div>
        )}
        <button
          type="button"
          className="disclosure"
          aria-expanded={expanded}
          aria-controls={layersId}
          onClick={() => setExpanded((open) => !open)}
        >
          <span className="disclosure-text">
            <span className="disclosure-title">Layers and date</span>
            <span className="disclosure-summary">{summary}</span>
          </span>
          <span className="disclosure-action">{expanded ? "Hide" : "Show"}</span>
        </button>
        <div id={layersId} className="panel-body" hidden={!expanded}>
          <LayerPanel
            date={date}
            minDate={minDate}
            maxDate={todayUtc()}
            onDateChange={changeDate}
            active={active}
            onToggle={toggleLayer}
            availability={availability}
            failedTiles={failedTiles}
          />
        </div>
      </header>
      <main className="map-area" aria-label={`Map of ${region.name}`}>
        <BaseMap
          region={region}
          overlays={overlays}
          onOverlayError={markFailed}
          getPadding={getPadding}
          onProblem={setProblem}
        />
      </main>
    </div>
  );
}
