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

export type StaticKey = "publish" | "contact" | "faq" | "privacy" | "legal" | "cookies" | "account" | "request" | "login";
/** Agency landing pages; the agency services themselves (code 95, licence exchange...) are service pages
 * resolved by the API from the services section. */
export type AgencyKey = "drivers";
export type ListKey = "work" | "services" | "documents" | "training" | "housingJobs";

export type AppRoute =
  | { type: "home" }
  | { type: "search" }
  | { type: "seller"; id: number }
  | { type: "companies" }
  | { type: "company"; slug: string }
  | { type: "blog" }
  | { type: "post"; slug: string }
  | { type: "static"; key: StaticKey }
  | { type: "agency"; key: AgencyKey }
  | { type: "list"; key: ListKey };

type Entry<K> = { key: K; slug: Localized; indexable: boolean };

/** Search across every section: what the home search falls back to when no section is chosen. */
export const SEARCH_PAGE: Entry<"search"> = {
  key: "search",
  slug: { es: "buscar", en: "search", uk: "poshuk", ru: "poisk" },
  indexable: false,
};

/** Articles: /es/blog and /es/blog/{slug} — the same word in every language, it reads everywhere. */
export const BLOG_PAGE: Entry<"blog"> = {
  key: "blog",
  slug: { es: "blog", en: "blog", uk: "blog", ru: "blog" },
  indexable: true,
};

export function blogPath(locale: Locale, slug?: string): string {
  const base = `${localePrefix(locale)}/${BLOG_PAGE.slug[locale]}`;
  return slug ? `${base}/${slug}` : base;
}

/** The directory of firms: /es/empresas and /es/empresas/{slug} */
export const COMPANIES_PAGE: Entry<"companies"> = {
  key: "companies",
  slug: { es: "empresas", en: "companies", uk: "firmy", ru: "firmy" },
  indexable: true,
};

export function companyPath(locale: Locale, slug?: string): string {
  const base = `${localePrefix(locale)}/${COMPANIES_PAGE.slug[locale]}`;
  return slug ? `${base}/${slug}` : base;
}

/** The public page of somebody who sells: /es/vendedor/42 */
export const SELLER_PAGE: Entry<"seller"> = {
  key: "seller",
  slug: { es: "vendedor", en: "seller", uk: "prodavets", ru: "prodavets" },
  indexable: false,
};

export function sellerPath(locale: Locale, id: number): string {
  return `${localePrefix(locale)}/${SELLER_PAGE.slug[locale]}/${id}`;
}

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
  { key: "login", slug: { es: "entrar", en: "sign-in", uk: "vhid", ru: "vhod" }, indexable: false },
];

/** spec §6: /es/conductores-ce (the service pages /es/servicios/cap-95 etc. come from the API) */
export const AGENCY_PAGES: Entry<AgencyKey>[] = [
  { key: "drivers", slug: { es: "conductores-ce", en: "ce-drivers", uk: "vodiiam-ce", ru: "voditelyam-ce" }, indexable: true },
];

/** List pages behind the header tabs; they match seeds/taxonomy.json, and old slugs are 301-ed by the API. */
export const LIST_PAGES: (Entry<ListKey> & { section: string; category?: string; feature?: string })[] = [
  { key: "work", section: "empleo", slug: { es: "empleo", en: "jobs", uk: "robota", ru: "rabota" }, indexable: true },
  { key: "services", section: "servicios", slug: { es: "nuestros-servicios", en: "our-services", uk: "nashi-posluhy", ru: "nashi-uslugi" }, indexable: true },
  { key: "documents", section: "servicios", category: "documentos", slug: { es: "nuestros-servicios/documentos", en: "our-services/documents", uk: "nashi-posluhy/dokumenty", ru: "nashi-uslugi/dokumenty" }, indexable: true },
  { key: "training", section: "servicios", category: "formacion", slug: { es: "nuestros-servicios/formacion", en: "our-services/training", uk: "nashi-posluhy/navchannia", ru: "nashi-uslugi/obuchenie" }, indexable: true },
  { key: "housingJobs", section: "empleo", feature: "housing", slug: { es: "empleo/con-alojamiento", en: "jobs/with-housing", uk: "robota/z-zhytlom", ru: "rabota/s-zhilyom" }, indexable: true },
];  // prettier-ignore

function entryOf(route: AppRoute): Entry<string> | undefined {
  if (route.type === "search") return SEARCH_PAGE;
  if (route.type === "static") return STATIC_PAGES.find((s) => s.key === route.key);
  if (route.type === "agency") return AGENCY_PAGES.find((s) => s.key === route.key);
  if (route.type === "list") return LIST_PAGES.find((s) => s.key === route.key);
  return undefined;
}

/** Full path with the locale prefix, e.g. "/ua/robota". */
export function localizedPath(locale: Locale, route: AppRoute): string {
  if (route.type === "seller") return sellerPath(locale, route.id);
  if (route.type === "companies") return companyPath(locale);
  if (route.type === "company") return companyPath(locale, route.slug);
  if (route.type === "blog") return blogPath(locale);
  if (route.type === "post") return blogPath(locale, route.slug);
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
  // /{lang}/{seller word}/{id}
  if (segments.length === 2 && /^\d+$/.test(segments[1])) {
    const wanted = SELLER_PAGE.slug[locale] === segments[0];
    if (wanted || LOCALES.some((l) => SELLER_PAGE.slug[l] === segments[0])) {
      return { route: { type: "seller", id: Number(segments[1]) }, redirect: !wanted };
    }
  }
  // /{lang}/blog[/{slug}]
  if (segments[0] === BLOG_PAGE.slug[locale] && segments.length <= 2) {
    return {
      route: segments.length === 2 ? { type: "post", slug: segments[1] } : { type: "blog" },
      redirect: false,
    };
  }
  // /{lang}/{firms word}[/{slug}]
  const firmsWord = segments[0];
  const isFirms = COMPANIES_PAGE.slug[locale] === firmsWord;
  if (segments.length <= 2 && (isFirms || LOCALES.some((l) => COMPANIES_PAGE.slug[l] === firmsWord))) {
    const route: AppRoute = segments.length === 2 ? { type: "company", slug: segments[1] } : { type: "companies" };
    return { route, redirect: !isFirms };
  }
  if (SEARCH_PAGE.slug[locale] === path) return { route: { type: "search" }, redirect: false };
  if (LOCALES.some((l) => SEARCH_PAGE.slug[l] === path)) return { route: { type: "search" }, redirect: true };
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
