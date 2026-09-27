import type { SalaryPeriod } from "./types";

export const MONTHLY_FACTOR: Record<SalaryPeriod, number> = { hour: 160, day: 21.7, week: 4.33, month: 1 };

export function formatEuro(value: number, locale: string): string {
  return `€${new Intl.NumberFormat(locale === "es" ? "es" : "uk", { useGrouping: true }).format(value)}`;
}

/** "2 h ago", "yesterday": coarse on purpose, so server and client render the same text. */
export function ago(iso: string | null, locale: string): string {
  if (!iso) return "";
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (minutes < 60) return rtf.format(-Math.max(minutes, 1), "minute");
  if (minutes < 60 * 24) return rtf.format(-Math.round(minutes / 60), "hour");
  return rtf.format(-Math.round(minutes / (60 * 24)), "day");
}

/** A value of a "from–to" filter: a year as it is ("2016", not "2 016"), anything else grouped. */
export function formatFilterNumber(filterKey: string, value: number, locale: string): string {
  return filterKey === "a.year" ? String(value) : new Intl.NumberFormat(locale).format(value);
}

/** "€2 800", "€16–18", "€2 800 – 3 200" */
export function formatSalaryRange(min: number | null, max: number | null, locale: string): string | null {
  if (min === null && max === null) return null;
  if (min !== null && max !== null && max !== min) return `${formatEuro(min, locale)}–${formatEuro(max, locale).slice(1)}`;
  return formatEuro((min ?? max) as number, locale);
}
