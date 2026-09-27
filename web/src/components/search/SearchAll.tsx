import { ArrowLeft, ArrowRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { AdCard } from "@/components/home/AdCard";
import { AdSearch } from "@/components/home/AdSearch";
import { SaveSearchButton } from "@/components/search/SaveSearchButton";
import { getAccount } from "@/lib/account";
import type { Locale } from "@/i18n/routing";
import { getHome, orFallback, searchEverything } from "@/lib/api";
import { localizedPath } from "@/lib/routes";
import type { RawSearchParams } from "@/lib/search-url";
import type { Home, SearchResponse } from "@/lib/types";

const EMPTY_HOME: Home = {
  totals: { listings: 0, today: 0, sections: 0 },
  sections: [],
  promoted: [],
  fresh: [],
};

const NO_RESULTS: SearchResponse["items"] = [];

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

/** Query params this page passes to the API; everything else (filters) belongs to the section pages. */
function apiParams(searchParams: RawSearchParams): [string, string][] {
  const pairs: [string, string][] = [];
  for (const key of ["q", "location", "sort", "page"] as const) {
    const value = searchParams[key];
    const single = Array.isArray(value) ? value[0] : value;
    if (single) pairs.push([key, single]);
  }
  return pairs;
}

export async function searchAllMetadata(locale: Locale, searchParams: RawSearchParams): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "search" });
  const q = searchParams.q;
  const query = Array.isArray(q) ? q[0] : q;
  return {
    title: query ? `«${query}» · ${t("everywhere")}` : t("everywhere"),
    robots: { index: false, follow: true },
  };
}

/** One search across every section: the home search box lands here when no section is chosen. */
export async function SearchAll({
  locale,
  searchParams,
}: {
  locale: Locale;
  searchParams: RawSearchParams;
}) {
  const t = await getTranslations("search");
  const account = await getAccount();
  const params = apiParams(searchParams);
  const q = one(searchParams.q);
  const [home, data] = await Promise.all([
    orFallback(getHome(locale), EMPTY_HOME),
    orFallback(searchEverything(locale, params), null),
  ]);
  const items = data?.items ?? NO_RESULTS;
  const page = data?.page ?? 1;
  const pages = data?.pages ?? 1;
  const pageHref = (n: number) => {
    const qs = new URLSearchParams(params.filter(([k]) => k !== "page"));
    if (n > 1) qs.set("page", String(n));
    const query = qs.toString();
    return `${localizedPath(locale, { type: "search" })}${query ? `?${query}` : ""}`;
  };

  return (
    <>
      <section className="home-search">
        <div className="container">
          <h1>{t("everywhere")}</h1>
          <AdSearch sections={home.sections} initialQuery={q} initialCity={one(searchParams.location) || null} />
        </div>
      </section>

      <div className="container home-content">
        <section className="home-block">
          <div className="home-block__head">
            <h2>{t("foundAds", { count: data?.total ?? 0 })}</h2>
            {q && (
              <SaveSearchButton
                title={q}
                params={Object.fromEntries(params)}
                signedIn={Boolean(account)}
                loginHref={localizedPath(locale, { type: "static", key: "login" })}
              />
            )}
          </div>

          {items.length === 0 ? (
            <div className="search-empty">
              <h2>{t("emptyTitle")}</h2>
              <p className="muted">{t("emptyText")}</p>
            </div>
          ) : (
            <ul className="ad-grid">
              {items.map((item) => (
                <li key={item.id}>
                  <AdCard listing={item} locale={locale} />
                </li>
              ))}
            </ul>
          )}

          {pages > 1 && (
            <nav className="pagination">
              {page > 1 ? (
                <Link href={pageHref(page - 1)} rel="prev">
                  <ArrowLeft size={15} aria-hidden /> {t("prev")}
                </Link>
              ) : (
                <span />
              )}
              <span className="muted">{t("pageOf", { page, total: pages })}</span>
              {page < pages ? (
                <Link href={pageHref(page + 1)} rel="next">
                  {t("next")} <ArrowRight size={15} aria-hidden />
                </Link>
              ) : (
                <span />
              )}
            </nav>
          )}
        </section>
      </div>
    </>
  );
}
