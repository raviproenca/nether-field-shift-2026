// AI-assisted: generated with Claude Code, reviewed by Ravi
// Region presets for the map. Source of truth: src/data/regions.py (PRESETS).
// Both files must keep the same bounding boxes; change them together.

export type RegionId = "sergipe" | "nordeste";

export interface Region {
  id: RegionId;
  name: string;
  /** West, south, east, north in degrees (WGS84), as in BBox(west, south, east, north). */
  bbox: [number, number, number, number];
}

export const REGIONS: readonly Region[] = [
  { id: "sergipe", name: "Sergipe", bbox: [-38.25, -11.57, -36.39, -9.51] },
  { id: "nordeste", name: "Nordeste", bbox: [-48.8, -18.4, -34.7, -1.0] },
];

export const DEFAULT_REGION_ID: RegionId = "sergipe";

export function getRegion(id: RegionId): Region {
  const region = REGIONS.find((candidate) => candidate.id === id);
  if (!region) {
    throw new Error(`Unknown region: ${id}`);
  }
  return region;
}

/** "38.25°W to 36.39°W, 11.57°S to 9.51°S" */
export function formatBbox([west, south, east, north]: Region["bbox"]): string {
  const lon = (value: number) => `${Math.abs(value).toFixed(2)}°${value < 0 ? "W" : "E"}`;
  const lat = (value: number) => `${Math.abs(value).toFixed(2)}°${value < 0 ? "S" : "N"}`;
  return `${lon(west)} to ${lon(east)}, ${lat(south)} to ${lat(north)}`;
}
