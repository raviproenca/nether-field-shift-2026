// AI-assisted: generated with Claude Code, reviewed by Ravi
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Region } from "./regions";
import { GIBS_CREDIT_URL, GIBS_LAYERS, type LayerId } from "./gibs/layers";
import { easeOut, MOVE_DURATION_MS, prefersReducedMotion } from "./motion";

const OSM_SOURCE_ID = "osm";
const OSM_MAX_ZOOM = 19;

const GIBS_CREDIT = `Imagery: <a href="${GIBS_CREDIT_URL}" target="_blank" rel="noopener">NASA GIBS / EOSDIS</a>`;

const gibsSourceId = (id: LayerId) => `gibs-${id}`;

// Tiles load on demand only, as the OSM tile usage policy asks; nothing is prefetched in bulk.
// GIBS layers start hidden (no requests) and get their date's tiles when switched on.
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
    ...Object.fromEntries(
      GIBS_LAYERS.map((layer) => [
        gibsSourceId(layer.id),
        { type: "raster", tiles: [layer.tiles], tileSize: 256, maxzoom: layer.maxZoom },
      ]),
    ),
  },
  layers: [
    { id: "osm-base", type: "raster", source: OSM_SOURCE_ID },
    ...GIBS_LAYERS.map(
      (layer): maplibregl.LayerSpecification => ({
        id: gibsSourceId(layer.id),
        type: "raster",
        source: gibsSourceId(layer.id),
        layout: { visibility: "none" },
      }),
    ),
  ],
};

export type MapProblem = "tiles" | "webgl" | null;

/** Tile URL for the selected date, or null to hide the layer. */
export type Overlays = Record<LayerId, string | null>;

interface BaseMapProps {
  region: Region;
  overlays: Overlays;
  onOverlayError: (id: LayerId) => void;
  /** Space the floating panel covers, so the region is framed beside it. */
  getPadding: () => maplibregl.PaddingOptions;
  onProblem: (problem: MapProblem) => void;
  /** Optional: called with the clicked position (the plot view picks its point this way). */
  onPick?: (lat: number, lon: number) => void;
  /** Optional: a marker for the picked point. */
  marker?: { lat: number; lon: number } | null;
}

export default function BaseMap({
  region,
  overlays,
  onOverlayError,
  getPadding,
  onProblem,
  onPick,
  marker = null,
}: BaseMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [styleReady, setStyleReady] = useState(false);
  const shownTiles = useRef(new Map<LayerId, string>());
  const initialRegion = useRef(region);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const latest = useRef({ getPadding, onProblem, onOverlayError, onPick });

  useEffect(() => {
    latest.current = { getPadding, onProblem, onOverlayError, onPick };
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
        attributionControl: { compact: false, customAttribution: GIBS_CREDIT },
      });
    } catch {
      latest.current.onProblem("webgl");
      return;
    }
    map.on("error", (event) => {
      if (!("sourceId" in event)) {
        return;
      }
      if (event.sourceId === OSM_SOURCE_ID) {
        latest.current.onProblem("tiles");
      }
      const gibsLayer = GIBS_LAYERS.find((layer) => gibsSourceId(layer.id) === event.sourceId);
      if (gibsLayer) {
        latest.current.onOverlayError(gibsLayer.id);
      }
    });
    map.on("click", (event) => latest.current.onPick?.(event.lngLat.lat, event.lngLat.lng));
    map.on("load", () => setStyleReady(true));
    map.on("data", (event) => {
      if (event.dataType === "source" && "tile" in event && event.sourceId === OSM_SOURCE_ID) {
        latest.current.onProblem(null);
      }
    });
    mapRef.current = map;
    const shown = shownTiles.current;
    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
      shown.clear();
      setStyleReady(false);
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) {
      return;
    }
    for (const layer of GIBS_LAYERS) {
      const tiles = overlays[layer.id];
      const sourceId = gibsSourceId(layer.id);
      if (tiles !== null && shownTiles.current.get(layer.id) !== tiles) {
        map.getSource<maplibregl.RasterTileSource>(sourceId)?.setTiles([tiles]);
        shownTiles.current.set(layer.id, tiles);
      }
      map.setLayoutProperty(sourceId, "visibility", tiles === null ? "none" : "visible");
    }
  }, [overlays, styleReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) {
      return;
    }
    if (!marker) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    markerRef.current ??= new maplibregl.Marker({ color: "#0a0a0a" }).setLngLat([marker.lon, marker.lat]).addTo(map);
    markerRef.current.setLngLat([marker.lon, marker.lat]);
  }, [marker, styleReady]);

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
