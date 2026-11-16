// AI-assisted: generated with Claude Code, reviewed by Ravi
// Which dates have imagery, read from GIBS DescribeDomains (answers in ~0.5 kB, CORS open).
import { addDays, fromDayNumber, toDayNumber, todayUtc } from "./dates";
import { domainsUrl, type GibsLayer } from "./layers";

const FIRST_DATE = "2000-01-01";
const DEFAULT_WINDOW_DAYS = 30;
const TIMEOUT_MS = 15_000;

interface Interval {
  start: number;
  end: number;
  stepDays: number;
}

export type Availability =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; intervals: Interval[]; first: string; last: string };

function parseInterval(text: string): Interval | null {
  const [start, end = start, period = "P1D"] = text.trim().split("/");
  const step = /^P(\d+)D$/.exec(period);
  if (!step) {
    return null;
  }
  return { start: toDayNumber(start), end: toDayNumber(end), stepDays: Number(step[1]) };
}

export function parseDomains(xml: string): Interval[] {
  const doc = new DOMParser().parseFromString(xml, "text/xml");
  const domain = doc.getElementsByTagName("Domain")[0]?.textContent ?? "";
  return domain
    .split(",")
    .filter((part) => part.trim() !== "")
    .map(parseInterval)
    .filter((interval): interval is Interval => interval !== null);
}

export async function fetchAvailability(layer: GibsLayer): Promise<Availability> {
  try {
    const response = await fetch(domainsUrl(layer, FIRST_DATE, todayUtc()), {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!response.ok) {
      return { status: "error" };
    }
    const intervals = parseDomains(await response.text());
    if (intervals.length === 0) {
      return { status: "error" };
    }
    const first = fromDayNumber(Math.min(...intervals.map((interval) => interval.start)));
    const last = fromDayNumber(Math.max(...intervals.map((interval) => interval.end)));
    return { status: "ready", intervals, first, last };
  } catch {
    return { status: "error" };
  }
}

function isOnStep(interval: Interval, day: number): boolean {
  return day >= interval.start && day <= interval.end && (day - interval.start) % interval.stepDays === 0;
}

export function hasData(availability: Availability, date: string): boolean {
  if (availability.status !== "ready") {
    return false;
  }
  const day = toDayNumber(date);
  return availability.intervals.some((interval) => isOnStep(interval, day));
}

/** The latest date with imagery on or before `date`, or null when the layer starts later. */
export function nearestEarlier(availability: Availability, date: string): string | null {
  if (availability.status !== "ready") {
    return null;
  }
  const day = toDayNumber(date);
  let best: number | null = null;
  for (const interval of availability.intervals) {
    if (interval.start > day) {
      continue;
    }
    const capped = Math.min(interval.end, day);
    const onStep = capped - ((capped - interval.start) % interval.stepDays);
    best = best === null ? onStep : Math.max(best, onStep);
  }
  return best === null ? null : fromDayNumber(best);
}

/** The most recent date in the last 30 days on which the most layers have imagery. */
export function pickDefaultDate(availabilities: Availability[], today = todayUtc()): string {
  let bestDate = addDays(today, -1);
  let bestCount = -1;
  for (let offset = 0; offset < DEFAULT_WINDOW_DAYS; offset += 1) {
    const date = addDays(today, -offset);
    const count = availabilities.filter((availability) => hasData(availability, date)).length;
    if (count > bestCount) {
      bestDate = date;
      bestCount = count;
    }
  }
  return bestDate;
}

/** Draw a layer on this date? Yes when GIBS lists the date, and also when the check failed (unknown). */
export function canShow(availability: Availability, date: string): boolean {
  return availability.status === "error" || hasData(availability, date);
}
