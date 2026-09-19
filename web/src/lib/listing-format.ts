import type { SalaryPeriod } from "./types";

export const MONTHLY_FACTOR: Record<SalaryPeriod, number> = { hour: 160, day: 21.7, week: 4.33, month: 1 };

export function formatEuro(value: number, locale: string): string {
  return `€${new Intl.NumberFormat(locale === "es" ? "es" : "uk", { useGrouping: true }).format(value)}`;
}

/** "€2 800", "€16–18", "€2 800 – 3 200" */
export function formatSalaryRange(min: number | null, max: number | null, locale: string): string | null {
  if (min === null && max === null) return null;
  if (min !== null && max !== null && max !== min) return `${formatEuro(min, locale)}–${formatEuro(max, locale).slice(1)}`;
  return formatEuro((min ?? max) as number, locale);
}
