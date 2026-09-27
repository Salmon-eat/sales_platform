import { X } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { permanentRedirect, redirect, unstable_rethrow } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { TrackSearch } from "@/components/Analytics";
import { ApplicationForm } from "@/components/apply/ApplicationForm";
import { AdRow } from "@/components/home/AdRow";
import { ListingCard } from "@/components/home/ListingCard";
import type { Locale } from "@/i18n/routing";
import { SaveSearchButton } from "@/components/search/SaveSearchButton";
import { getAccount } from "@/lib/account";
import { orFallback, resolvePath, searchListings } from "@/lib/api";
import { getApplicationOptions } from "@/lib/application-options";
import { FEATURE_SLUGS, type Linker, type ListState, listPath, makeLinker } from "@/lib/list-url";
import { LIST_PAGES, localizedPath, prefixed } from "@/lib/routes";
import {
  get,
  type Pairs,
  pairsFromSearchParams,
  parsePairs,
  type RawSearchParams,
  samePairs,
  setParam,
  sortPairs,
} from "@/lib/search-url";
import { formatFilterNumber } from "@/lib/listing-format";
import { isJobsSection } from "@/lib/sections";
import { absoluteUrl, apiAlternates, jsonLd } from "@/lib/seo";
import type { ResolveOut, SearchResponse } from "@/lib/types";

import { FiltersPanel } from "./FiltersPanel";
import { FiltersSheet } from "./FiltersSheet";
import { QuickFilters } from "./QuickFilters";
import { SearchBox } from "./SearchBox";

const TIER2_CHIP_KEYS = ["no_language", "no_experience", "salary_min", "schedule", "contract", "posted", "radius"];

function stateOf(resolved: ResolveOut): ListState {
  return {
    section: resolved.section!,
    sector: resolved.sector,
    profession: resolved.profession,
    feature: resolved.feature,
    location: resolved.location?.slug ?? null,
  };
}

async function load(locale: Locale, resolved: ResolveOut, searchParams: RawSearchParams, revalidate: number | false = false) {
  const state = stateOf(resolved);
  const current = pairsFromSearchParams(searchParams);
  const api: Pairs = current.filter(([k]) => k !== "housing" && k !== "category" && k !== "location" && !k.startsWith("utm_"));
  const category = resolved.profession?.slug ?? resolved.sector?.slug;
  if (category) api.push(["category", category]);
  if (resolved.location) api.push(["location", resolved.location.slug]);
  if (resolved.feature === "housing") api.push(["housing", "1"]);
  const data = await searchListings(locale, resolved.section!.key, api, revalidate);
  // housing is expressed by the path segment, not the query
  const canonical = sortPairs(parsePairs(data.canonical_query).filter(([k]) => !(resolved.feature && k === "housing")));
  return { state, current, data, canonical };
}

async function names(locale: Locale, resolved: ResolveOut) {
  const t = await getTranslations({ locale, namespace: "seo" });
  const base = resolved.profession?.name ?? resolved.sector?.name ?? resolved.section!.name;
  const what = resolved.feature ? t("withHousing", { what: base }) : base;
  const loc = resolved.location;
  const where = !loc ? t("whereSpain") : loc.level === "provincia" ? t("province", { name: loc.name }) : loc.name;
  return { what, where, t };
}

export async function listMetadata(locale: Locale, resolved: ResolveOut, searchParams: RawSearchParams): Promise<Metadata> {
  const { data, canonical } = await load(locale, resolved, searchParams);
  const { what, where, t } = await names(locale, resolved);
  const page = Number(get(canonical, "page") ?? 1);
  // spec §6: query filters -> noindex, follow + canonical without query; page=2+ -> self canonical, indexed
  const filtered = canonical.some(([k]) => k !== "page");
  const indexable = resolved.indexable && !filtered;
  const title = resolved.title_override ?? t("title", { what, where, count: data.total });
  return {
    title: page > 1 ? `${title} · ${page}` : title,
    description: resolved.description_override ?? t("description", { what, where, count: data.total }),
    alternates: indexable ? apiAlternates(locale, resolved.alternates, page > 1 ? `?page=${page}` : "") : apiAlternates(locale, { [locale]: resolved.alternates[locale] }),
    robots: indexable ? undefined : { index: false, follow: true },
  };
}

export async function ListPage({
  locale,
  resolved,
  searchParams,
}: {
  locale: Locale;
  resolved: ResolveOut;
  searchParams: RawSearchParams;
}) {
  const t = await getTranslations("search");
  const account = await getAccount();
  const loaded = await load(locale, resolved, searchParams);
  const { state, data, canonical } = loaded;
  // ad tags (utm_*) survive the canonical redirects: the site tracker reads them on the landing page
  const utm = loaded.current.filter(([k]) => k.startsWith("utm_"));
  const current = loaded.current.filter(([k]) => !k.startsWith("utm_"));
  const withQuery = (target: string, pairs: Pairs) => withQueryString(target, [...pairs, ...utm]);
  const link = makeLinker(locale, state);
  const path = listPath(locale, state);

  // stage-3 links (?category=&location=) and a query understood as profession + city -> path (spec §7)
  const legacy = [get(current, "category"), get(current, "location")].filter(Boolean);
  if (legacy.length || get(current, "housing")) {
    const housing = state.feature || get(current, "housing") ? FEATURE_SLUGS.housing[locale] : null;
    // sector/profession order is fixed by the resolver (a profession without its sector -> 301)
    const segments = [
      state.section.slug,
      state.sector?.slug,
      state.profession?.slug,
      get(current, "category"),
      housing,
      state.location ?? get(current, "location"),
    ];
    // a profession from the query has no sector yet: resolve once so the client gets a single 301
    let target = segments.filter(Boolean).join("/");
    const checked = await resolvePath(locale, target).catch(() => null);
    if (checked?.type === "redirect" && checked.redirect) target = checked.redirect;
    permanentRedirect(withQuery(prefixed(locale, target), canonical.filter(([k]) => !["housing", "category", "location"].includes(k))));
  }
  if (data.understood?.complete && !state.sector && !state.location) {
    const segments = [state.section.slug, data.understood.category?.slug, data.understood.location?.slug].filter(Boolean);
    redirect(withQuery(prefixed(locale, segments.join("/")), setParam(canonical, "q", null)));
  }
  if (!samePairs(current, canonical)) permanentRedirect(withQuery(path, canonical));

  const { what, where } = await names(locale, resolved);
  const tSeo = await getTranslations("seo");
  const heading = tSeo("titleNoCount", { what, where });
  const q = get(canonical, "q");

  const crumbs = [
    { name: "Citobazar", href: localizedPath(locale, { type: "home" }) },
    { name: state.section.name, href: link({ sector: null, feature: null, location: null }) },
    ...(state.sector ? [{ name: state.sector.name, href: link({ profession: null, feature: null, location: null }) }] : []),
    ...(state.profession ? [{ name: state.profession.name, href: link({ feature: null, location: null }) }] : []),
    ...(resolved.location ? [{ name: resolved.location.name, href: link({}) }] : []),
  ];

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd([
          {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: crumbs.map((c, i) => ({ "@type": "ListItem", position: i + 1, name: c.name, item: absoluteUrl(c.href) })),
          },
          {
            "@context": "https://schema.org",
            "@type": "ItemList",
            numberOfItems: data.total,
            itemListElement: data.items.map((item, i) => ({
              "@type": "ListItem",
              position: (data.page - 1) * data.per_page + i + 1,
              url: absoluteUrl(prefixed(locale, item.path)),
              name: item.title,
            })),
          },
        ])}
      />
      <section className="search-hero">
        <div className="container">
          <nav className="breadcrumbs" aria-label="breadcrumbs">
            {crumbs.slice(0, -1).map((c) => (
              <span key={c.href} className="crumb">
                <Link href={c.href}>{c.name}</Link>
                <span aria-hidden>›</span>
              </span>
            ))}
            <span>{crumbs[crumbs.length - 1].name}</span>
          </nav>
        </div>
      </section>

      <Catalog
        locale={locale}
        data={data}
        canonical={canonical}
        state={state}
        path={path}
        head={
          <>
            <SearchBox
              key={path}
              sectionPaths={{ empleo: localizedPath(locale, { type: "list", key: "work" }), servicios: localizedPath(locale, { type: "list", key: "services" }) }}
              // a word recognised as a profession became a path: show it back, so the box never looks
              // as if the site swallowed what was typed
              initialQuery={q ?? state.profession?.name ?? state.sector?.name ?? ""}
              initialPlace={resolved.location && resolved.location.level === "municipio" ? { slug: resolved.location.slug, name: resolved.location.name } : null}
            />
            <h1>{heading}</h1>
            <SaveSearchButton
              title={heading}
              sectionKey={state.section.key}
              categorySlug={state.profession?.slug ?? state.sector?.slug ?? null}
              locationSlug={state.location}
              params={Object.fromEntries(canonical)}
              signedIn={Boolean(account)}
              loginHref={localizedPath(locale, { type: "static", key: "login" })}
            />
          </>
        }
      />
    </>
  );
}

/** Home page (L0): the jobs catalog right under the hero; filters lead to the indexable list pages. */
export async function HomeCatalog({ locale }: { locale: Locale }) {
  const section = LIST_PAGES.find((p) => p.key === "work")!.slug[locale];
  try {
    const resolved = await resolvePath(locale, section);
    if (resolved.type !== "list") return null;
    // cached for 60 s like the rest of the home page, so it stays statically regenerated (ISR)
    const { state, data, canonical } = await load(locale, resolved, {}, 60);
    return <Catalog locale={locale} data={data} canonical={canonical} state={state} path={listPath(locale, state)} />;
  } catch (error) {
    unstable_rethrow(error);
    console.error("HomeCatalog", error);
    return null; // API down: the rest of the home page still renders
  }
}

type CatalogProps = {
  locale: Locale;
  data: SearchResponse;
  canonical: Pairs;
  state: ListState;
  path: string;
  /** list pages: the search box and the heading, above the results and level with the filters */
  head?: ReactNode;
};

/** Filters panel (desktop) / bottom sheet (mobile) + results; used by list pages and the home page. */
export async function Catalog({ locale, data, canonical, state, path, head }: CatalogProps) {
  const t = await getTranslations("search");
  const link = makeLinker(locale, state);
  const chips = activeChips(data, canonical, state, link, t, locale);
  // jobs are compared by salary and shown as job cards; everything else by price, with its photo
  const jobs = isJobsSection(state.section.key);
  const Card = jobs ? ListingCard : AdRow;
  const foundKey = jobs ? "found" : "foundAds"; // "3 вакансії" / "3 оголошення"
  // "we will find you a job" belongs in the jobs section; on a page of sofas it is nonsense
  const applyOptions = data.total === 0 && jobs ? await getApplicationOptions(locale) : null;
  // A page that says "nothing found" and stops is a dead end: whatever the search was, the section
  // still has its newest ads, and they are better than an apology.
  const instead =
    data.total === 0
      ? await orFallback(searchListings(locale, state.section.key, [["sort", "new"]], 120), null)
      : null;
  const q = get(canonical, "q");
  const sortOptions = [...(q ? ["relevance"] : []), "new", ...(jobs ? ["salary"] : ["price_asc", "price_desc"])] as (
    | "relevance"
    | "new"
    | "salary"
    | "price_asc"
    | "price_desc"
  )[];

  return (
    <div className={head ? "container search-layout search-layout--head" : "container search-layout"}>
      {head && <div className="search-head">{head}</div>}
      <FiltersSheet
        total={data.total}
        activeCount={chips.length}
        labels={{ filters: t("filters"), close: t("close"), show: t("showResults", { count: data.total }) }}
      >
        <FiltersPanel data={data} pairs={canonical} state={state} link={link} />
      </FiltersSheet>

      <section className="search-results">
        {q && <TrackSearch q={q} found={data.total} />}
        <QuickFilters data={data} pairs={canonical} state={state} link={link} />
        <div className="search-toolbar">
          {/* only the jobs section counts vacancies; everywhere else these are ads */}
          <p className="search-count">
            {t(foundKey, { count: data.total })}
          </p>
          <div className="chips-row">
            {chips.map((chip) => (
              <Link key={chip.key} href={chip.href} scroll={false} className="chip" aria-label={t("removeFilter")}>
                {chip.label} <X size={13} aria-hidden />
              </Link>
            ))}
            {chips.length > 1 && (
              <Link href={link({ sector: null, feature: null, location: null }, q ? [["q", q]] : [])} className="chip chip--reset">
                {t("reset")}
              </Link>
            )}
          </div>
          <nav className="sort" aria-label={t("sort")}>
            {sortOptions.map((s) => (
              <Link
                key={s}
                href={link({}, setParam(canonical, "sort", s === (q ? "relevance" : "new") ? null : s))}
                scroll={false}
                className={data.sort === s ? "sort-link sort-link--active" : "sort-link"}
                rel="nofollow"
              >
                {t(`sort_${s}`)}
              </Link>
            ))}
          </nav>
        </div>

        {data.understood && !data.understood.complete && (data.understood.category || data.understood.location) && (
          <p className="search-hint">
            {t("didYouMean")}{" "}
            <Link
              href={withQueryString(
                prefixed(locale, [state.section.slug, data.understood.category?.slug, data.understood.location?.slug].filter(Boolean).join("/")),
                data.understood.rest_q ? [["q", data.understood.rest_q]] : [],
              )}
            >
              {[data.understood.category?.name, data.understood.location?.name, data.understood.rest_q].filter(Boolean).join(" · ")}
            </Link>
          </p>
        )}
        {data.corrected && data.corrected.length > 0 && (
          <p className="search-hint">
            {t("correctedTo", {
              typed: data.corrected.map(([typed]) => typed).join(", "),
              used: data.corrected.map(([, used]) => used).join(", "),
            })}
          </p>
        )}
        {/* "пилосос" with no vacuum for sale: say that these are the neighbours, not the thing asked for */}
        {data.close_enough && q && (
          <p className="search-hint">{t("closeEnough", { q, category: data.close_enough.category })}</p>
        )}
        {data.fuzzy && data.total > 0 && !data.close_enough && <p className="search-hint">{t("fuzzyNote")}</p>}

        {data.total === 0 ? (
          <div className="search-empty">
            <h2>{q ? t("noExactMatch", { q }) : t("emptyTitle")}</h2>
            {data.relaxations.length > 0 && (
              <>
                <p className="muted">{t("emptyText")}</p>
                <ul className="relaxations">
                  {data.relaxations.map((r) => {
                    const pairs = parsePairs(r.query).filter(([k]) => k !== "housing");
                    const target =
                      r.kind === "province" && r.location
                        ? link({ location: r.location }, pairs)
                        : r.kind === "spain"
                          ? link({ location: null }, pairs)
                          : link({}, pairs);
                    return (
                      <li key={r.kind}>
                        <Link href={target} className={r.count === 0 ? "relaxation relaxation--zero" : "relaxation"}>
                          <span>{t(`relax_${r.kind}`, { value: r.label_value ?? "" })}</span>
                          <span className="facet-count">
                            {t(foundKey, { count: r.count })}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
            {applyOptions && (
              <div className="search-apply">
                <p className="muted">{t("pickJobText")}</p>
                <ApplicationForm sectors={applyOptions.sectors} cities={applyOptions.cities} title={t("pickJobTitle")} />
              </div>
            )}
            {instead && instead.items.length > 0 && (
              <>
                <h3>{t("insteadTitle", { section: state.section.name })}</h3>
                <ul className="search-list">
                  {instead.items.slice(0, 6).map((item) => (
                    <li key={item.id}>
                      <Card listing={item} locale={locale} />
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        ) : (
          <ul className="search-list">
            {data.items.map((item) => (
              <li key={item.id}>
                <Card
                  listing={item}
                  locale={locale}
                  note={
                    item.distance_km !== null && data.location && item.location?.slug !== data.location.slug
                      ? t("distance", { km: Math.round(item.distance_km), city: data.location.name })
                      : undefined
                  }
                />
              </li>
            ))}
          </ul>
        )}

        {data.pages > 1 && (
          <nav className="pagination">
            {data.page > 1 ? (
              <Link href={withQueryString(path, setParam(canonical, "page", data.page > 2 ? String(data.page - 1) : null))} rel="prev">
                {t("prev")}
              </Link>
            ) : (
              <span />
            )}
            <span className="muted">{t("pageOf", { page: data.page, total: data.pages })}</span>
            {data.page < data.pages ? (
              <Link href={withQueryString(path, sortPairs([...canonical.filter(([k]) => k !== "page"), ["page", String(data.page + 1)]]))} rel="next">
                {t("next")}
              </Link>
            ) : (
              <span />
            )}
          </nav>
        )}
      </section>
    </div>
  );
}

function withQueryString(path: string, pairs: Pairs): string {
  const query = pairs.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v).replace(/%2C/gi, ",")}`).join("&");
  return query ? `${path}?${query}` : path;
}

type Translate = Awaited<ReturnType<typeof getTranslations<"search">>>;

function activeChips(data: SearchResponse, pairs: Pairs, state: ListState, link: Linker, t: Translate, locale: Locale) {
  const chips: { key: string; label: string; href: string }[] = [];
  const q = get(pairs, "q");
  if (q) chips.push({ key: "q", label: `«${q}»`, href: link({}, setParam(pairs, "q", null)) });
  if (state.profession) chips.push({ key: "profession", label: state.profession.name, href: link({ profession: null }, pairs) });
  else if (state.sector) chips.push({ key: "sector", label: state.sector.name, href: link({ sector: null }, pairs) });
  if (state.feature) chips.push({ key: "housing", label: t("housing"), href: link({ feature: null }, pairs) });
  if (data.location) chips.push({ key: "location", label: data.location.name, href: link({ location: null }, setParam(pairs, "radius", null)) });
  for (const key of TIER2_CHIP_KEYS) {
    const value = get(pairs, key);
    if (!value) continue;
    for (const v of value.split(",")) {
      const label =
        key === "salary_min"
          ? t("salaryValue", { amount: v })
          : key === "radius"
            ? t("radiusValue", { km: v })
            : ["no_language", "no_experience"].includes(key)
              ? t(key as "no_language")
              : t(`${key}_${v}` as "schedule_full");
      const rest = value.split(",").filter((x) => x !== v).join(",");
      chips.push({ key: `${key}:${v}`, label, href: link({}, setParam(pairs, key, rest || null)) });
    }
  }
  // "from–to": one chip for the whole range, "Рік: 2015–2020", "Ціна: до 8 000 €"
  for (const group of data.facets.filter((g) => g.type === "range")) {
    const { chosen_from: lo, chosen_to: hi } = group;
    if (lo === null && hi === null) continue;
    const n = (v: number) => formatFilterNumber(group.key, v, locale);
    const span = lo !== null && hi !== null ? `${n(lo)}–${n(hi)}` : lo !== null ? t("rangeFromValue", { value: n(lo) }) : t("rangeToValue", { value: n(hi!) });
    const unit = group.key === "price" ? " €" : group.unit ? ` ${group.unit}` : "";
    chips.push({
      key: group.key,
      label: `${group.label ?? t(group.key as "price")}: ${span}${unit}`,
      href: link({}, setParam(pairs, group.key, null)),
    });
  }
  // attributes of the profession (tier 3) and tags of the section (tier 2) share the a.<key> form
  for (const group of data.facets.filter((g) => g.key.startsWith("a.") && g.type !== "range")) {
    const value = get(pairs, group.key);
    if (!value) continue;
    for (const v of value.split(",")) {
      const option = group.values.find((o) => o.value === v);
      const rest = value.split(",").filter((x) => x !== v).join(",");
      chips.push({
        key: `${group.key}:${v}`,
        label: group.type === "bool" ? (group.label ?? v) : `${group.label}: ${option?.label ?? v}`,
        href: link({}, setParam(pairs, group.key, rest || null)),
      });
    }
  }
  return chips;
}
