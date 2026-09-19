import type { Metadata } from "next";

import { LOCALES, type Locale, X_DEFAULT_LOCALE } from "@/i18n/routing";

import { type AppRoute, isIndexable, localizedPath, prefixed } from "./routes";

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/** canonical + hreflang for all 4 languages + x-default (es), built from the entity, not the URL. */
export function routeAlternates(locale: Locale, route: AppRoute): Metadata["alternates"] {
  return {
    canonical: localizedPath(locale, route),
    languages: {
      ...Object.fromEntries(LOCALES.map((l) => [l, localizedPath(l, route)])),
      "x-default": localizedPath(X_DEFAULT_LOCALE, route),
    },
  };
}

/** Alternates from the API (paths without prefix). Only languages present get an hreflang. */
export function apiAlternates(locale: Locale, alternates: Partial<Record<Locale, string>>, canonicalSuffix = "") {
  const languages: Record<string, string> = {};
  for (const l of LOCALES) if (alternates[l]) languages[l] = prefixed(l, alternates[l] as string);
  if (alternates[X_DEFAULT_LOCALE]) languages["x-default"] = prefixed(X_DEFAULT_LOCALE, alternates[X_DEFAULT_LOCALE] as string);
  return {
    canonical: `${prefixed(locale, alternates[locale] ?? "")}${canonicalSuffix}`,
    languages,
  } satisfies Metadata["alternates"];
}

export function routeRobots(route: AppRoute): Metadata["robots"] {
  return isIndexable(route) ? undefined : { index: false, follow: true };
}

export function absoluteUrl(path: string): string {
  return new URL(path, SITE_URL).toString();
}

/** <script type="application/ld+json"> payload; "<" is escaped so text can't close the tag. */
export function jsonLd(data: unknown): { __html: string } {
  return { __html: JSON.stringify(data).replace(/</g, "\\u003c") };
}
