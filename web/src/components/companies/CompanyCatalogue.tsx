import { BadgeCheck, Building2, MapPin, Search, Star } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import { apiFetch } from "@/lib/api";
import { companyPath } from "@/lib/routes";
import type { RawSearchParams } from "@/lib/search-url";
import type { CompanyCard } from "@/lib/types";

type Page = { items: CompanyCard[]; total: number; page: number; per_page: number };

const EMPTY: Page = { items: [], total: 0, page: 1, per_page: 20 };

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

async function load(locale: Locale, searchParams: RawSearchParams): Promise<Page> {
  const query = new URLSearchParams({ lang: locale });
  const q = one(searchParams.q);
  const city = one(searchParams.city);
  const page = one(searchParams.page);
  if (q) query.set("q", q);
  if (city) query.set("city", city);
  if (/^\d+$/.test(page)) query.set("page", page);
  return apiFetch<Page>(`/companies?${query}`, { revalidate: 60 }).catch(() => EMPTY);
}

export async function companiesMetadata(locale: Locale): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "companies" });
  return { title: t("title"), description: t("subtitle") };
}

/** The directory: who does what, where, and how they are rated. */
export async function CompanyCatalogue({
  locale,
  searchParams,
}: {
  locale: Locale;
  searchParams: RawSearchParams;
}) {
  const t = await getTranslations("companies");
  const data = await load(locale, searchParams);
  const q = one(searchParams.q);

  return (
    <div className="container static-page">
      <section className="seller-head">
        <h1>{t("title")}</h1>
        <p className="muted">{t("subtitle")}</p>
      </section>

      <form className="ad-search company-search" role="search" action={companyPath(locale)}>
        <label className="ad-search__field">
          <Search size={18} aria-hidden />
          <input name="q" type="search" defaultValue={q} placeholder={t("searchPlaceholder")} aria-label={t("searchPlaceholder")} />
        </label>
        <button type="submit" className="btn btn--primary ad-search__submit">
          {t("search")}
        </button>
      </form>

      <p className="muted small">{t("found", { count: data.total })}</p>

      {data.items.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <ul className="company-list">
          {data.items.map((firm) => (
            <li key={firm.id} className="company-row">
              <span className="company-row__logo">
                {firm.logo ? <img src={firm.logo} alt="" /> : <Building2 size={22} aria-hidden />}
              </span>
              <div className="company-row__body">
                <h2>
                  <Link href={companyPath(locale, firm.slug)} className="listing-link">
                    {firm.name}
                  </Link>
                  {firm.is_verified && (
                    <span className="badge badge--active" title={t("verifiedHint")}>
                      <BadgeCheck size={13} aria-hidden /> {t("verified")}
                    </span>
                  )}
                </h2>
                <p className="company-row__meta muted small">
                  {firm.city_name && (
                    <>
                      <MapPin size={13} aria-hidden /> {firm.city_name}
                      {" · "}
                    </>
                  )}
                  {firm.categories.join(" · ")}
                  {firm.rating !== null && (
                    <>
                      {" · "}
                      <Star size={13} aria-hidden /> {firm.rating.toFixed(1)} (
                      {t("reviews", { count: firm.reviews_count })})
                    </>
                  )}
                </p>
                {firm.about && <p className="company-row__about">{firm.about.slice(0, 200)}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
