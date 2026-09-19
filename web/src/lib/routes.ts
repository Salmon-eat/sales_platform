/**
 * Pages known to the web app itself: home, static pages, agency landing pages and the list pages the
 * header tabs point to. Everything else under /{lang}/ (sections, sectors, professions, cities, cards)
 * is resolved by GET /v1/resolve (spec §6).
 *
 * Pages are identified by keys, not URL strings, so the language switcher and hreflang always point at
 * the real equivalent page.
 */
import { type Locale, LOCALES, localePrefix } from "@/i18n/routing";

type Localized = Record<Locale, string>;

export type StaticKey = "publish" | "contact" | "faq" | "privacy" | "legal" | "cookies" | "account" | "request";
/** Agency landing pages; the agency services themselves (code 95, licence exchange...) are service pages
 * resolved by the API from the services section. */
export type AgencyKey = "drivers";
export type ListKey = "work" | "services" | "documents" | "training" | "housingJobs";

export type AppRoute =
  | { type: "home" }
  | { type: "static"; key: StaticKey }
  | { type: "agency"; key: AgencyKey }
  | { type: "list"; key: ListKey };

type Entry<K> = { key: K; slug: Localized; indexable: boolean };

export const STATIC_PAGES: Entry<StaticKey>[] = [
  { key: "publish", slug: { es: "publicar-oferta", en: "post-a-job", uk: "rozmistyty-oholoshennia", ru: "razmestit-obyavlenie" }, indexable: true },
  { key: "contact", slug: { es: "contacto", en: "contact", uk: "kontakty", ru: "kontakty" }, indexable: true },
  // "didn't find a job?": a request for the manager to find work (or help with anything else)
  { key: "request", slug: { es: "te-buscamos-trabajo", en: "find-me-a-job", uk: "pidberemo-robotu", ru: "podberem-rabotu" }, indexable: true },
  { key: "faq", slug: { es: "preguntas-frecuentes", en: "faq", uk: "pytannia", ru: "voprosy" }, indexable: true },
  // spec §6: static pages are indexed "always, except the policy"
  { key: "privacy", slug: { es: "privacidad", en: "privacy", uk: "konfidentsiinist", ru: "konfidentsialnost" }, indexable: false },
  // LSSI art. 10 (owner of the site) and the cookie / browser storage policy
  { key: "legal", slug: { es: "aviso-legal", en: "legal-notice", uk: "pravova-informatsiia", ru: "pravovaya-informatsiya" }, indexable: false },
  { key: "cookies", slug: { es: "politica-de-cookies", en: "cookie-policy", uk: "polityka-cookies", ru: "politika-cookies" }, indexable: false },
  { key: "account", slug: { es: "cuenta", en: "account", uk: "kabinet", ru: "kabinet" }, indexable: false },
];

/** spec §6: /es/conductores-ce (the service pages /es/servicios/cap-95 etc. come from the API) */
export const AGENCY_PAGES: Entry<AgencyKey>[] = [
  { key: "drivers", slug: { es: "conductores-ce", en: "ce-drivers", uk: "vodiiam-ce", ru: "voditelyam-ce" }, indexable: true },
];

/** List pages behind the header tabs; they match seeds/taxonomy.json, and old slugs are 301-ed by the API. */
export const LIST_PAGES: (Entry<ListKey> & { section: string; category?: string; feature?: string })[] = [
  { key: "work", section: "empleo", slug: { es: "empleo", en: "jobs", uk: "robota", ru: "rabota" }, indexable: true },
  { key: "services", section: "servicios", slug: { es: "servicios", en: "services", uk: "posluhy", ru: "uslugi" }, indexable: true },
  { key: "documents", section: "servicios", category: "documentos", slug: { es: "servicios/documentos", en: "services/documents", uk: "posluhy/dokumenty", ru: "uslugi/dokumenty" }, indexable: true },
  { key: "training", section: "servicios", category: "formacion", slug: { es: "servicios/formacion", en: "services/training", uk: "posluhy/navchannia", ru: "uslugi/obuchenie" }, indexable: true },
  { key: "housingJobs", section: "empleo", feature: "housing", slug: { es: "empleo/con-alojamiento", en: "jobs/with-housing", uk: "robota/z-zhytlom", ru: "rabota/s-zhilyom" }, indexable: true },
];  // prettier-ignore

function entryOf(route: AppRoute): Entry<string> | undefined {
  if (route.type === "static") return STATIC_PAGES.find((s) => s.key === route.key);
  if (route.type === "agency") return AGENCY_PAGES.find((s) => s.key === route.key);
  if (route.type === "list") return LIST_PAGES.find((s) => s.key === route.key);
  return undefined;
}

/** Full path with the locale prefix, e.g. "/ua/robota". */
export function localizedPath(locale: Locale, route: AppRoute): string {
  const entry = entryOf(route);
  return entry ? `${localePrefix(locale)}/${entry.slug[locale]}` : localePrefix(locale);
}

/** API paths come without the language prefix. */
export function prefixed(locale: Locale, path: string): string {
  return path ? `${localePrefix(locale)}/${path.replace(/^\/+/, "")}` : localePrefix(locale);
}

export function isIndexable(route: AppRoute): boolean {
  return route.type === "home" || Boolean(entryOf(route)?.indexable);
}

export type Resolved = { route: AppRoute; /** set when the slug belongs to another language */ redirect: boolean };

/** Static and agency pages only; returns null for everything the API resolves. */
export function resolveSegments(locale: Locale, segments: string[]): Resolved | null {
  if (segments.length === 0) return { route: { type: "home" }, redirect: false };
  const path = segments.join("/");
  for (const [type, entries] of [["static", STATIC_PAGES], ["agency", AGENCY_PAGES]] as const) {
    for (const entry of entries) {
      if (entry.slug[locale] === path) return { route: { type, key: entry.key } as AppRoute, redirect: false };
      if (LOCALES.some((l) => entry.slug[l] === path)) {
        return { route: { type, key: entry.key } as AppRoute, redirect: true };
      }
    }
  }
  return null;
}
