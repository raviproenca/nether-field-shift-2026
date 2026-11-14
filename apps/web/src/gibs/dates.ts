// AI-assisted: generated with Claude Code, reviewed by Ravi
// Calendar dates as "YYYY-MM-DD" strings, always in UTC (GIBS dates are UTC days).

const DAY_MS = 86_400_000;

export function toDayNumber(date: string): number {
  return Math.floor(Date.parse(`${date.slice(0, 10)}T00:00:00Z`) / DAY_MS);
}

export function fromDayNumber(day: number): string {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

export function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

export function addDays(date: string, days: number): string {
  return fromDayNumber(toDayNumber(date) + days);
}

const LONG_DATE = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "UTC" });

/** "Nov 10, 2026" */
export function formatDate(date: string): string {
  return LONG_DATE.format(new Date(`${date}T00:00:00Z`));
}
