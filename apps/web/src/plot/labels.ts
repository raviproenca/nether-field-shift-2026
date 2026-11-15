// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import type { Copy } from "./i18n";
import type { Crop, Diagnosis, Priority, Projection } from "./types";

export const CROP_IDS: readonly Crop[] = ["maize", "beans", "cassava"];
export const PRIORITY_IDS: readonly Priority[] = ["water", "soil", "erosion", "income"];

export interface Metric {
  label: string;
  value: number | null;
  unit: string;
  /** Source id in Recommendation.sources, or "derived" for a number the engine computed from the others. */
  sourceId: string;
}

/** Each observed number and the dataset it comes from (source ids as the engine lists them). */
export function diagnosisMetrics(d: Diagnosis, c: Copy): Metric[] {
  const m = c.metrics;
  return [
    { label: m.rain_total, value: d.rain_total_mm, unit: c.units.mm, sourceId: "imerg" },
    { label: m.rain_daily, value: d.rain_daily_mean_mm, unit: c.units.mmDay, sourceId: "imerg" },
    { label: m.et0_daily, value: d.et0_daily_mean_mm, unit: c.units.mmDay, sourceId: "power" },
    { label: m.water_balance, value: d.water_balance_mm, unit: c.units.mm, sourceId: "derived" },
    { label: m.soil_moisture, value: d.soil_moisture_surface_m3m3, unit: "m³/m³", sourceId: "smap" },
    { label: m.temperature_mean, value: d.temperature_mean_c, unit: "°C", sourceId: "power" },
    { label: m.temperature_max, value: d.temperature_max_c, unit: "°C", sourceId: "power" },
    { label: m.ndvi, value: d.ndvi_mean, unit: "", sourceId: "viirs" },
    { label: m.elevation, value: d.elevation_m, unit: "m", sourceId: "srtm" },
    { label: m.slope, value: d.slope_mean_pct, unit: "%", sourceId: "srtm" },
  ];
}

export function projectionMetrics(p: Projection, c: Copy): Metric[] {
  const m = c.metrics;
  return [
    { label: m.forecast_rain_total, value: p.rain_total_mm, unit: c.units.mm, sourceId: "open-meteo" },
    { label: m.rain_daily, value: p.rain_daily_mean_mm, unit: c.units.mmDay, sourceId: "open-meteo" },
    { label: m.et0_daily, value: p.et0_daily_mean_mm, unit: c.units.mmDay, sourceId: "open-meteo" },
    { label: m.water_balance, value: p.water_balance_mm, unit: c.units.mm, sourceId: "open-meteo" },
    { label: m.temperature_mean, value: p.temperature_mean_c, unit: "°C", sourceId: "open-meteo" },
    { label: m.temperature_max, value: p.temperature_max_c, unit: "°C", sourceId: "open-meteo" },
  ];
}

export const formatNumber = (value: number | null, unit: string, noData: string): string =>
  value === null ? noData : `${Number(value.toFixed(2))}${unit ? ` ${unit}` : ""}`;
