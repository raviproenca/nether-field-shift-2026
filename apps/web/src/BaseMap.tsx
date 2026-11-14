// AI-assisted: generated with Claude Code, reviewed by Ravi
import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Region } from "./regions";
import { easeOut, MOVE_DURATION_MS, prefersReducedMotion } from "./motion";

const OSM_SOURCE_ID = "osm";
const OSM_MAX_ZOOM = 19;

// Tiles load on demand only, as the OSM tile usage policy asks; nothing is prefetched in bulk.
const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    [OSM_SOURCE_ID]: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: OSM_MAX_ZOOM,
      attribution:
        '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a>',
    },
  },
  layers: [{ id: "osm-base", type: "raster", source: OSM_SOURCE_ID }],
};

export type MapProblem = "tiles" | "webgl" | null;

interface BaseMapProps {
  region: Region;
  /** Space the floating panel covers, so the region is framed beside it. */
  getPadding: () => maplibregl.PaddingOptions;
  onProblem: (problem: MapProblem) => void;
}

export default function BaseMap({ region, getPadding, onProblem }: BaseMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const initialRegion = useRef(region);
  const latest = useRef({ getPadding, onProblem });

  useEffect(() => {
    latest.current = { getPadding, onProblem };
  });

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: BASE_STYLE,
        bounds: initialRegion.current.bbox,
        fitBoundsOptions: { padding: latest.current.getPadding() },
        maxZoom: OSM_MAX_ZOOM,
        attributionControl: { compact: false },
      });
    } catch {
      latest.current.onProblem("webgl");
      return;
    }
    map.on("error", (event) => {
      if ("sourceId" in event && event.sourceId === OSM_SOURCE_ID) {
        latest.current.onProblem("tiles");
      }
    });
    map.on("data", (event) => {
      if (event.dataType === "source" && "tile" in event && event.sourceId === OSM_SOURCE_ID) {
        latest.current.onProblem(null);
      }
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || region === initialRegion.current) {
      return;
    }
    initialRegion.current = region;
    const animate = !prefersReducedMotion();
    map.fitBounds(region.bbox, {
      padding: latest.current.getPadding(),
      animate,
      duration: animate ? MOVE_DURATION_MS : 0,
      easing: easeOut,
    });
  }, [region]);

  return <div ref={containerRef} className="map" />;
}
