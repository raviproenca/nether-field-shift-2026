// AI-assisted: generated with Claude Code, reviewed by Ravi
import { useCallback, useRef, useState } from "react";
import BaseMap, { type MapProblem } from "./BaseMap";
import RegionSelector from "./RegionSelector";
import { DEFAULT_REGION_ID, formatBbox, getRegion, type RegionId } from "./regions";

const PROBLEM_MESSAGES: Record<Exclude<MapProblem, null>, string> = {
  tiles: "Map tiles couldn't load. Check your connection, then reload.",
  webgl: "This browser can't draw the map because WebGL is off or not supported.",
};

// Breathing room around the framed region, in px (space scale: 4 px steps).
const FRAME_GAP = 24;

export default function App() {
  const [regionId, setRegionId] = useState<RegionId>(DEFAULT_REGION_ID);
  const [problem, setProblem] = useState<MapProblem>(null);
  const panelRef = useRef<HTMLElement>(null);
  const region = getRegion(regionId);

  const getPadding = useCallback(() => {
    const panelBottom = panelRef.current?.getBoundingClientRect().bottom ?? 0;
    return { top: panelBottom + FRAME_GAP, right: FRAME_GAP, bottom: FRAME_GAP, left: FRAME_GAP };
  }, []);

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
      </header>
      <main className="map-area" aria-label={`Map of ${region.name}`}>
        <BaseMap region={region} getPadding={getPadding} onProblem={setProblem} />
      </main>
    </div>
  );
}
