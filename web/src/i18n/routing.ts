import { defineRouting } from "next-intl/routing";

// Internal codes are ISO 639-1 ("uk" = Ukrainian) so hreflang/html lang stay valid for Google;
// the URL prefix for Ukrainian is /ua.
export const LOCALES = ["es", "en", "uk", "ru"] as const;
export type Locale = (typeof LOCALES)[number];

// Local guard instead of next-intl's hasLocale: next-intl's AppConfig types depend on this file.
export function isLocale(value: string | undefined): value is Locale {
  return (LOCALES as readonly string[]).includes(value ?? "");
}

/** Main language of the product: x-default in hreflang and the language crawlers get on "/". */
export const X_DEFAULT_LOCALE: Locale = "es";

const envDefault = process.env.NEXT_PUBLIC_DEFAULT_LOCALE;

export const routing = defineRouting({
  locales: LOCALES,
  // uk while developing, es in production (see .env.example).
  defaultLocale: isLocale(envDefault) ? envDefault : X_DEFAULT_LOCALE,
  localePrefix: { mode: "always", prefixes: { uk: "/ua" } },
});

export const LOCALE_LABELS: Record<Locale, string> = { es: "ES", en: "EN", uk: "UA", ru: "RU" };

export function localePrefix(locale: Locale): string {
  return locale === "uk" ? "/ua" : `/${locale}`;
}

export function localeFromPrefix(segment: string | undefined): Locale | undefined {
  if (segment === "ua") return "uk";
  return isLocale(segment) && segment !== "uk" ? segment : undefined;
}

export function asLocale(value: string): Locale {
  return isLocale(value) ? value : routing.defaultLocale;
}
