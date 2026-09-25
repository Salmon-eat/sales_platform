import { BadgeCheck, Building2, Clock, Globe, MapPin, Star } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AdCard } from "@/components/home/AdCard";
import { CompanyContactButton } from "@/components/companies/CompanyContactButton";
import type { Locale } from "@/i18n/routing";
import { ApiError, apiFetch } from "@/lib/api";
import { companyPath } from "@/lib/routes";
import { absoluteUrl, jsonLd } from "@/lib/seo";
import type { CompanyPageData } from "@/lib/types";

async function load(slug: string, locale: Locale): Promise<CompanyPageData> {
  try {
    return await apiFetch<CompanyPageData>(`/companies/${encodeURIComponent(slug)}?lang=${locale}`, {
      revalidate: 60,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function companyMetadata(locale: Locale, slug: string): Promise<Metadata> {
  const firm = await load(slug, locale);
  return {
    title: firm.name,
    description: firm.about.slice(0, 200) || undefined,
    alternates: { canonical: absoluteUrl(companyPath(locale, firm.slug)) },
  };
}

/** One firm: what it does, where it is, how it is rated, and what it has on the site now. */
export async function CompanyPage({ locale, slug }: { locale: Locale; slug: string }) {
  const t = await getTranslations("companies");
  const ts = await getTranslations("seller");
  const firm = await load(slug, locale);
  const since = new Intl.DateTimeFormat(locale, { year: "numeric", month: "long", timeZone: "Europe/Madrid" });

  return (
    <div className="container static-page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd({
          "@context": "https://schema.org",
          "@type": "LocalBusiness",
          name: firm.name,
          description: firm.about || undefined,
          address: firm.address
            ? { "@type": "PostalAddress", streetAddress: firm.address, addressLocality: firm.city_name ?? undefined, addressCountry: "ES" }
            : undefined,
          url: absoluteUrl(companyPath(locale, firm.slug)),
          ...(firm.rating !== null
            ? { aggregateRating: { "@type": "AggregateRating", ratingValue: firm.rating, reviewCount: firm.reviews_count } }
            : {}),
        })}
      />

      <section className="company-head">
        <span className="company-head__logo">
          {firm.logo ? <img src={firm.logo} alt="" /> : <Building2 size={30} aria-hidden />}
        </span>
        <div>
          <h1>
            {firm.name}
            {firm.is_verified && (
              <span className="badge badge--active">
                <BadgeCheck size={14} aria-hidden /> {t("verified")}
              </span>
            )}
          </h1>
          <p className="muted company-head__meta">
            {firm.categories.join(" · ")}
            {firm.rating !== null && (
              <>
                {" · "}
                <Star size={14} aria-hidden /> {firm.rating.toFixed(1)} ({t("reviews", { count: firm.reviews_count })})
              </>
            )}
            {" · "}
            {t("since", { date: since.format(new Date(firm.created_at)) })}
          </p>
        </div>
      </section>

      <div className="company-layout">
        <div>
          {firm.about && (
            <section className="home-block">
              <div className="home-block__head">
                <h2>{t("about")}</h2>
              </div>
              <p className="company-about" lang={firm.lang}>
                {firm.about}
              </p>
            </section>
          )}

          {firm.listings.length > 0 && (
            <section className="home-block">
              <div className="home-block__head">
                <h2>{t("theirAds")}</h2>
              </div>
              <ul className="ad-grid">
                {firm.listings.map((item) => (
                  <li key={item.id}>
                    <AdCard listing={item} locale={locale} />
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="home-block">
            <div className="home-block__head">
              <h2>{ts("reviews")}</h2>
            </div>
            {firm.reviews.length === 0 ? (
              <p className="muted">{ts("noReviewsYet")}</p>
            ) : (
              <ul className="review-list">
                {firm.reviews.map((review) => (
                  <li key={review.id} className="review">
                    <div className="review__head">
                      <strong>{review.author_name}</strong>
                      <span className="muted small">{review.rating}★</span>
                    </div>
                    {review.text && <p>{review.text}</p>}
                    {review.reply && (
                      <p className="review__reply">
                        <strong>{ts("sellerReplied")}:</strong> {review.reply}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <p className="muted small">
              <Link href={`/${locale === "uk" ? "ua" : locale}/prodavets/${firm.owner_id}`} className="listing-link">
                {t("allAboutSeller")}
              </Link>
            </p>
          </section>
        </div>

        <aside className="company-aside">
          <CompanyContactButton slug={firm.slug} />
          <dl className="company-facts">
            {firm.city_name && (
              <div>
                <dt>
                  <MapPin size={14} aria-hidden /> {t("where")}
                </dt>
                <dd>
                  {firm.city_name}
                  {firm.address ? `, ${firm.address}` : ""}
                </dd>
              </div>
            )}
            {firm.hours && (
              <div>
                <dt>
                  <Clock size={14} aria-hidden /> {t("hours")}
                </dt>
                <dd>{firm.hours}</dd>
              </div>
            )}
            {firm.site && (
              <div>
                <dt>
                  <Globe size={14} aria-hidden /> {t("site")}
                </dt>
                <dd>
                  <a href={firm.site} rel="nofollow noopener">
                    {firm.site.replace(/^https?:\/\//, "")}
                  </a>
                </dd>
              </div>
            )}
          </dl>
        </aside>
      </div>
    </div>
  );
}
