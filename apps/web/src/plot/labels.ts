// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import type { Crop, Diagnosis, Priority, Projection } from "./types";

export const CROPS: readonly { id: Crop; label: string }[] = [
  { id: "maize", label: "Maize" },
  { id: "beans", label: "Beans" },
  { id: "cassava", label: "Cassava" },
];

export const PRIORITIES: readonly { id: Priority; label: string }[] = [
  { id: "water", label: "Save water" },
  { id: "soil", label: "Protect soil" },
  { id: "erosion", label: "Control erosion" },
  { id: "income", label: "Income" },
];

/** Engine trade-off codes, in plain English. */
export const TRADE_OFF_LABELS: Record<string, string> = {
  keeps_current_calendar: "Keeps the current calendar and routine",
  favors_cover_and_soil: "Favors soil cover and soil health",
  favors_forage_or_income: "Favors forage and income",
};

export const STRATEGY_TITLES: Record<string, string> = {
  current_practice: "Current practice",
  soil_water_conservation: "Soil and water conservation",
  resilient_income_forage: "Resilient income and forage",
};

export const cropLabel = (id: string): string => CROPS.find((crop) => crop.id === id)?.label ?? id;

export interface Metric {
  label: string;
  value: number | null;
  unit: string;
  /** Source id in Recommendation.sources, or "derived" for a number the engine computed from the others. */
  sourceId: string;
}

/** Each observed number and the dataset it comes from (source ids as the engine lists them). */
export function diagnosisMetrics(d: Diagnosis): Metric[] {
  return [
    { label: "Rain in the period", value: d.rain_total_mm, unit: "mm", sourceId: "imerg" },
    { label: "Mean daily rain", value: d.rain_daily_mean_mm, unit: "mm/day", sourceId: "imerg" },
    { label: "Mean daily ET0", value: d.et0_daily_mean_mm, unit: "mm/day", sourceId: "power" },
    { label: "Water balance", value: d.water_balance_mm, unit: "mm", sourceId: "derived" },
    { label: "Surface soil moisture", value: d.soil_moisture_surface_m3m3, unit: "m³/m³", sourceId: "smap" },
    { label: "Mean temperature", value: d.temperature_mean_c, unit: "°C", sourceId: "power" },
    { label: "Maximum temperature", value: d.temperature_max_c, unit: "°C", sourceId: "power" },
    { label: "Vegetation index (NDVI)", value: d.ndvi_mean, unit: "", sourceId: "viirs" },
    { label: "Elevation", value: d.elevation_m, unit: "m", sourceId: "srtm" },
    { label: "Mean slope", value: d.slope_mean_pct, unit: "%", sourceId: "srtm" },
  ];
}

export function projectionMetrics(p: Projection): Metric[] {
  return [
    { label: "Forecast rain", value: p.rain_total_mm, unit: "mm", sourceId: "open-meteo" },
    { label: "Mean daily rain", value: p.rain_daily_mean_mm, unit: "mm/day", sourceId: "open-meteo" },
    { label: "Mean daily ET0", value: p.et0_daily_mean_mm, unit: "mm/day", sourceId: "open-meteo" },
    { label: "Water balance", value: p.water_balance_mm, unit: "mm", sourceId: "open-meteo" },
    { label: "Mean temperature", value: p.temperature_mean_c, unit: "°C", sourceId: "open-meteo" },
    { label: "Maximum temperature", value: p.temperature_max_c, unit: "°C", sourceId: "open-meteo" },
  ];
}

export const formatNumber = (value: number | null, unit: string): string =>
  value === null ? "No data" : `${Number(value.toFixed(2))}${unit ? ` ${unit}` : ""}`;

export const formatDay = (iso: string): string =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
