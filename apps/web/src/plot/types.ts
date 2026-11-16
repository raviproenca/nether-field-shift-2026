// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
// Types mirror docs/data-format/recommendation.schema.json and the POST /recommendation response (#53).

export type Crop = "maize" | "beans" | "cassava";
export type Priority = "water" | "soil" | "erosion" | "income";

export interface RecommendationRequest {
  lat: number;
  lon: number;
  radius_km: number;
  crop: Crop;
  previous_crops?: Crop[];
  priority: Priority;
  lang: "en" | "pt-BR";
}

export interface SourceAttribution {
  source: string;
  dataset: string;
  nasa: boolean;
  url: string;
  doi: string | null;
  notice: string | null;
}

export interface Diagnosis {
  period_start: string;
  period_end: string;
  rain_total_mm: number | null;
  rain_daily_mean_mm: number | null;
  et0_daily_mean_mm: number | null;
  water_balance_mm: number | null;
  soil_moisture_surface_m3m3: number | null;
  soil_moisture_root_kgm2: number | null;
  temperature_mean_c: number | null;
  temperature_max_c: number | null;
  ndvi_mean: number | null;
  elevation_m: number | null;
  slope_mean_pct: number | null;
  sources: SourceAttribution[];
}

export interface Projection {
  period_start: string;
  period_end: string;
  horizon_days: number;
  available: boolean;
  rain_total_mm: number | null;
  rain_daily_mean_mm: number | null;
  temperature_mean_c: number | null;
  temperature_max_c: number | null;
  et0_daily_mean_mm: number | null;
  water_balance_mm: number | null;
  sources: SourceAttribution[];
}

export interface CropSchedule {
  crop: string;
  planting_start: string;
  planting_end: string;
  cycle_days: number;
  water_demand_mm: number;
}

export interface Action {
  code: string;
  summary: string;
  timing: string;
  evidence: string;
}

export interface Strategy {
  kind: string;
  rank: number;
  score: number;
  title: string;
  crops: string[];
  trade_offs: string[];
  planting_schedule: CropSchedule[];
  water_demand_mm: number;
  breaks_pest_cycle: boolean;
  pest_cycle_note: string;
  actions: Action[];
}

export interface Recommendation {
  schema_version: 1;
  plot: {
    lat: number;
    lon: number;
    radius_km: number;
    id?: string | null;
    name: string | null;
    elevation_m: number | null;
    previous_crops?: string[];
  };
  crop: Crop;
  priority: Priority;
  diagnosis: Diagnosis;
  projection: Projection;
  strategies: Strategy[];
  uncertainty_note: string;
  validation_note: string;
  sources: SourceAttribution[];
}

export interface RecommendationResponse {
  recommendation: Recommendation;
  explanation: string;
  lang: "en" | "pt-BR";
  /** Only on saved results (demo files): when the engine run was made. */
  generated_at?: string;
}

/** Error envelope shared by every API route (#49). */
export interface ApiErrorBody {
  error: { code: string; message: string };
}
