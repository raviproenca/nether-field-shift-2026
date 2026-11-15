// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Seasonal rain risk for any point, computed in the browser from NASA POWER daily rain and the
// shared settings in public/risk/common.json (written by scripts/build_risk_cache.py).
import type { RiskData } from "./RiskChart";

interface RiskSettings {
  first_year: number;
  last_year: number;
  decendios: number[];
  strong_el_nino_years: number[];
  windows: RiskData["windows"];
  sources: RiskData["sources"];
}

const POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point";
const FILL = -999;

function decendio(month: number, day: number): number {
  return (month - 1) * 3 + Math.min(Math.floor((day - 1) / 10), 2) + 1;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/** year -> decendio -> rain (mm), keeping only seasons with every day from April 1 to July 31. */
export function seasonsByDecendio(daily: Record<string, number>, settings: RiskSettings): Map<number, Map<number, number>> {
  const seasons = new Map<number, { rain: Map<number, number>; days: number }>();
  for (const [stamp, value] of Object.entries(daily)) {
    const year = Number(stamp.slice(0, 4));
    const month = Number(stamp.slice(4, 6));
    const day = Number(stamp.slice(6, 8));
    if (month < 4 || month > 7 || year < settings.first_year || year > settings.last_year || value === FILL) continue;
    const season = seasons.get(year) ?? { rain: new Map(), days: 0 };
    const key = decendio(month, day);
    season.rain.set(key, (season.rain.get(key) ?? 0) + value);
    season.days += 1;
    seasons.set(year, season);
  }
  const complete = new Map<number, Map<number, number>>();
  for (const [year, season] of seasons) {
    if (season.days === 122) complete.set(year, season.rain);
  }
  return complete;
}

export function riskFromSeasons(seasons: Map<number, Map<number, number>>, settings: RiskSettings): RiskData | null {
  const strong = settings.strong_el_nino_years.filter((year) => seasons.has(year));
  const others = [...seasons.keys()].filter((year) => !strong.includes(year));
  if (!strong.length || !others.length) return null;
  const round = (value: number) => Math.round(value * 10) / 10;
  return {
    decendios: settings.decendios.map((d) => ({
      decendio: d,
      strong_el_nino_mm: round(median(strong.map((year) => seasons.get(year)!.get(d) ?? 0))),
      other_years_mm: round(median(others.map((year) => seasons.get(year)!.get(d) ?? 0))),
    })),
    strong_el_nino_years: strong,
    other_years_count: others.length,
    windows: settings.windows,
    sources: settings.sources,
  };
}

export async function fetchLiveRisk(lat: number, lon: number, signal?: AbortSignal): Promise<RiskData | null> {
  const settingsResponse = await fetch(`${import.meta.env.BASE_URL}risk/common.json`, { signal });
  if (!settingsResponse.ok) return null;
  const settings = (await settingsResponse.json()) as RiskSettings;
  const params = new URLSearchParams({
    parameters: "PRECTOTCORR",
    community: "AG",
    latitude: lat.toFixed(4),
    longitude: lon.toFixed(4),
    start: `${settings.first_year}0101`,
    end: `${settings.last_year}1231`,
    format: "JSON",
  });
  const response = await fetch(`${POWER_URL}?${params}`, { signal });
  if (!response.ok) return null;
  const body = (await response.json()) as { properties?: { parameter?: { PRECTOTCORR?: Record<string, number> } } };
  const daily = body.properties?.parameter?.PRECTOTCORR;
  return daily ? riskFromSeasons(seasonsByDecendio(daily, settings), settings) : null;
}
