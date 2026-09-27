import { ArrowLeft, ArrowRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { Building2 } from "lucide-react";

import { AdCard } from "@/components/home/AdCard";
import { AdSearch } from "@/components/home/AdSearch";
import { SaveSearchButton } from "@/components/search/SaveSearchButton";
import { getAccount } from "@/lib/account";
import { companyPath } from "@/lib/routes";
import type { CompanyCard } from "@/lib/types";
import type { Locale } from "@/i18n/routing";
import { getHome, orFallback, searchCompanies, searchEverything } from "@/lib/api";
import { localizedPath, prefixed } from "@/lib/routes";
import type { RawSearchParams } from "@/lib/search-url";
import type { Home, SearchResponse } from "@/lib/types";

const EMPTY_HOME: Home = {
  totals: { listings: 0, today: 0, sections: 0 },
  sections: [],
  promoted: [],
  fresh: [],
};

const NO_RESULTS: SearchResponse["items"] = [];
const NO_FIRMS: { items: CompanyCard[]; total: number } = { items: [], total: 0 };

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
  const tc = await getTranslations("companies");
  const th = await getTranslations("home");
  const account = await getAccount();
  const params = apiParams(searchParams);
  const q = one(searchParams.q);
  const [home, data, firms] = await Promise.all([
    orFallback(getHome(locale), EMPTY_HOME),
    orFallback(searchEverything(locale, params), null),
    q ? orFallback(searchCompanies(locale, q), NO_FIRMS) : Promise.resolve(NO_FIRMS),
  ]);
  const items = data?.items ?? NO_RESULTS;
  const page = data?.page ?? 1;
  const pages = data?.pages ?? 1;
  // "юридичні послуги" is a category we know, even when not one ad carries those words: the section
  // page is the answer, and without the section the path cannot be built at all
  const understood = data?.understood;
  // only a query we understood whole: "продам холодильник" reads "продам" as the sales profession and
  // suggesting it would send the visitor somewhere they never asked to go
  const understoodHref =
    understood?.section_slug && !understood.rest_q && (understood.category || understood.location)
      ? prefixed(
          locale,
          [understood.section_slug, understood.category?.slug, understood.location?.slug]
            .filter(Boolean)
            .join("/"),
        )
      : null;
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
        {/* a request like "legal services in Málaga" is usually answered by a firm, not by an ad */}
        {firms.items.length > 0 && (
          <section className="home-block">
            <div className="home-block__head">
              <h2>{tc("title")}</h2>
              <Link href={companyPath(locale)} className="home-block__link">
                {tc("found", { count: firms.total })}
              </Link>
            </div>
            <ul className="company-list">
              {firms.items.slice(0, 3).map((firm) => (
                <li key={firm.id} className="company-row">
                  <span className="company-row__logo">
                    {firm.logo ? <img src={firm.logo} alt="" /> : <Building2 size={20} aria-hidden />}
                  </span>
                  <div className="company-row__body">
                    <h3>
                      <Link href={companyPath(locale, firm.slug)} className="listing-link">
                        {firm.name}
                      </Link>
                      {firm.is_verified && <span className="badge badge--active">{tc("verified")}</span>}
                    </h3>
                    <p className="company-row__meta muted small">
                      {[firm.city_name, ...firm.categories].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

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

          {data?.corrected && data.corrected.length > 0 && (
            <p className="search-hint">
              {t("correctedTo", {
                typed: data.corrected.map(([typed]) => typed).join(", "),
                used: data.corrected.map(([, used]) => used).join(", "),
              })}
            </p>
          )}

          {items.length === 0 ? (
            <div className="search-empty">
              <h2>{t("emptyTitle")}</h2>
              {/* the word was recognised even though no ad carries it: send the visitor to the
                  section it belongs to instead of leaving them on an empty page */}
              {understoodHref ? (
                <>
                  <p className="muted">{t("didYouMean")}</p>
                  <Link href={understoodHref} className="search-empty__link">
                    {[understood?.category?.name, understood?.location?.name].filter(Boolean).join(" · ")}
                  </Link>
                </>
              ) : (
                <p className="muted">{t("emptyHint")}</p>
              )}
              {/* the section we point at may be empty too, so there is always something to look at */}
              {home.fresh.length > 0 && (
                <>
                  <h3>{th("freshTitle")}</h3>
                  <ul className="ad-grid">
                    {home.fresh.slice(0, 4).map((item) => (
                      <li key={item.id}>
                        <AdCard listing={item} locale={locale} />
                      </li>
                    ))}
                  </ul>
                </>
              )}
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
