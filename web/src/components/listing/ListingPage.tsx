import { Building2, CalendarDays, MapPin, Send } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { TrackListingView } from "@/components/Analytics";
import { ApplicationForm } from "@/components/apply/ApplicationForm";
import { ListingCard } from "@/components/home/ListingCard";
import { PhotoGallery } from "@/components/listing/PhotoGallery";
import { SellerContact } from "@/components/listing/SellerContact";
import { AppliedNotice } from "@/components/saved/AppliedNotice";
import { FavoriteButton } from "@/components/saved/FavoriteButton";
import type { Locale } from "@/i18n/routing";
import { getAccount } from "@/lib/account";
import { ApiError, getListingDetail } from "@/lib/api";
import { getApplicationOptions } from "@/lib/application-options";
import { formatEuro } from "@/lib/listing-format";
import { localizedPath, prefixed } from "@/lib/routes";
import { absoluteUrl, apiAlternates, jsonLd } from "@/lib/seo";
import type { ListingDetail, ResolveOut } from "@/lib/types";

const TELEGRAM_BOT = process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/";
const LANG_LABEL: Record<string, string> = { es: "ES", en: "EN", uk: "UA", ru: "RU" };
const UNIT: Record<string, string> = { hour: "HOUR", day: "DAY", week: "WEEK", month: "MONTH" };
const PRICE_PERIOD = { month: "perMonth", week: "perWeek", day: "perDay", hour: "perHour" } as const;

async function load(id: number, locale: Locale): Promise<ListingDetail> {
  try {
    return await getListingDetail(id, locale);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

function place(listing: ListingDetail, spainWide: string): string {
  return listing.location_scope === "spain_wide" ? spainWide : (listing.location?.name ?? "");
}

function salaryText(listing: ListingDetail, locale: Locale, t: (k: "perHour" | "perDay" | "perWeek") => string) {
  const amount = listing.salary_min ?? listing.salary_max;
  if (amount === null) return null;
  const range = listing.salary_max && listing.salary_min && listing.salary_max !== listing.salary_min;
  const value = range ? `${formatEuro(listing.salary_min!, locale)}–${formatEuro(listing.salary_max!, locale).slice(1)}` : formatEuro(amount, locale);
  const suffix = { hour: t("perHour"), day: t("perDay"), week: t("perWeek"), month: "" }[listing.salary_period ?? "month"];
  return `${value}${suffix}`;
}

export async function listingMetadata(locale: Locale, resolved: ResolveOut): Promise<Metadata> {
  const listing = await load(resolved.listing_id!, locale);
  const t = await getTranslations({ locale, namespace: "seo" });
  const tl = await getTranslations({ locale, namespace: "listing" });
  const tp = await getTranslations({ locale, namespace: "listingPage" });
  const where = place(listing, tp("spainWide"));
  const salary = salaryText(listing, locale, tl) ?? tl("salaryNone");
  return {
    title: t("listingTitle", { title: listing.title, where }),
    description: t("listingDescription", { title: listing.title, where, salary }).slice(0, 300),
    // indexed only in languages with a text and while open or closed < 30 days (spec §2, §6)
    alternates: resolved.indexable ? apiAlternates(locale, resolved.alternates) : { canonical: prefixed(locale, resolved.alternates[locale] ?? listing.path) },
    robots: resolved.indexable ? undefined : { index: false, follow: true },
    openGraph: { title: listing.title, type: "article" },
  };
}

export async function ListingPage({ locale, resolved }: { locale: Locale; resolved: ResolveOut }) {
  const listing = await load(resolved.listing_id!, locale);
  const t = await getTranslations("listingPage");
  const tl = await getTranslations("listing");
  const ts = await getTranslations("search");
  const tsel = await getTranslations("seller");
  const options = await getApplicationOptions(locale);
  const closed = listing.state !== "active";
  // an ad somebody posted about their own thing: contacts and a chat, not an application form
  const fromPerson = listing.source === "private";
  const account = fromPerson ? await getAccount() : null;
  const where = place(listing, t("spainWide"));
  const salary = salaryText(listing, locale, tl);
  // outside jobs the number people look for is the price, not a salary
  const price =
    listing.price_kind === "free"
      ? tl("priceFree")
      : listing.price != null
        ? `${formatEuro(listing.price, locale)}${listing.price_period ? tl(PRICE_PERIOD[listing.price_period]) : ""}`
        : listing.price_kind === "negotiable"
          ? tl("priceAsk")
          : null;
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "Europe/Madrid" });
  // "5 places", "start 1 October", "3 months": set by the manager in the "Набір" block
  const facts = [
    listing.vacancies && { label: t("vacancies"), value: String(listing.vacancies) },
    listing.start_date && { label: t("startDate"), value: date.format(new Date(`${listing.start_date}T12:00:00`)) },
    listing.duration_months && { label: t("duration"), value: t("months", { count: listing.duration_months }) },
  ].filter((f): f is { label: string; value: string } => Boolean(f));
  const [sector, profession] = listing.category_path.length === 2 ? listing.category_path : [listing.category_path[0], null];

  const sectionPath = prefixed(locale, listing.section_slug);
  const crumbs = [
    { name: "Citobazar", href: localizedPath(locale, { type: "home" }) },
    { name: listing.section_name, href: sectionPath },
    { name: sector.name, href: `${sectionPath}/${sector.slug}` },
    ...(profession ? [{ name: profession.name, href: `${sectionPath}/${sector.slug}/${profession.slug}` }] : []),
    ...(listing.location
      ? [{ name: listing.location.name, href: `${sectionPath}/${sector.slug}${profession ? `/${profession.slug}` : ""}/${listing.location.slug}` }]
      : []),
  ];
  const url = absoluteUrl(prefixed(locale, listing.path));

  const jobPosting = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: listing.title,
    description: [listing.description, listing.requirements, listing.conditions]
      .filter(Boolean)
      .map((p) => `<p>${String(p).replace(/&/g, "&amp;").replace(/</g, "&lt;")}</p>`)
      .join(""),
    identifier: { "@type": "PropertyValue", name: "Citobazar", value: String(listing.id) },
    datePosted: listing.published_at,
    validThrough: listing.expires_at,
    employmentType: [
      ...(listing.schedule.includes("full") ? ["FULL_TIME"] : []),
      ...(listing.schedule.includes("part") || listing.schedule.includes("weekends") ? ["PART_TIME"] : []),
      ...(listing.contract === "temporal" || listing.contract === "fijo_discontinuo" ? ["TEMPORARY"] : []),
    ],
    hiringOrganization: {
      "@type": "Organization",
      name: listing.source === "agency" ? "Citobazar" : (listing.employer_name ?? "Citobazar"),
      sameAs: absoluteUrl("/"),
    },
    jobLocation: {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressCountry: "ES",
        ...(listing.location ? { addressLocality: listing.location.name } : {}),
        ...(listing.province ? { addressRegion: listing.province.name } : {}),
      },
      ...(listing.lat !== null ? { geo: { "@type": "GeoCoordinates", latitude: listing.lat, longitude: listing.lon } } : {}),
    },
    ...(listing.location_scope === "spain_wide" ? { applicantLocationRequirements: { "@type": "Country", name: "ES" } } : {}),
    ...(listing.salary_period && (listing.salary_min ?? listing.salary_max) !== null
      ? {
          baseSalary: {
            "@type": "MonetaryAmount",
            currency: "EUR",
            value: {
              "@type": "QuantitativeValue",
              ...(listing.salary_min !== null ? { minValue: listing.salary_min } : {}),
              ...(listing.salary_max !== null ? { maxValue: listing.salary_max } : {}),
              unitText: UNIT[listing.salary_period],
            },
          },
        }
      : {}),
    directApply: true,
    url,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd([
          ...(closed ? [] : [jobPosting]),
          {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: crumbs.map((c, i) => ({ "@type": "ListItem", position: i + 1, name: c.name, item: absoluteUrl(c.href) })),
          },
        ])}
      />
      <section className="page-hero listing-hero">
        <div className="container">
          <nav className="breadcrumbs" aria-label="breadcrumbs">
            {crumbs.map((c, i) => (
              <span key={c.href} className="crumb">
                {i > 0 && <span aria-hidden>›</span>}
                <Link href={c.href}>{c.name}</Link>
              </span>
            ))}
          </nav>
          <h1 lang={listing.lang === "uk" ? "uk" : listing.lang}>{listing.title}</h1>
          <div className="listing-hero-meta">
            <span>
              <Building2 size={15} aria-hidden /> {listing.source === "agency" ? tl("agencyName") : (listing.employer_name ?? "—")}
            </span>
            <span>
              <MapPin size={15} aria-hidden /> {where}
              {listing.province && listing.location && listing.province.name !== listing.location.name && `, ${listing.province.name}`}
            </span>
            {listing.published_at && (
              <span>
                <CalendarDays size={15} aria-hidden /> {t("published", { date: date.format(new Date(listing.published_at)) })}
              </span>
            )}
            <FavoriteButton id={listing.id} withLabel />
          </div>
          {/* narrow screens: the form is below the description, this takes the person there */}
          {!closed && (
            <a href="#apply" className="btn btn--primary btn--lg listing-apply-jump">
              {fromPerson ? tsel("contactJump") : tl("apply")}
            </a>
          )}
        </div>
      </section>

      <div className="container listing-layout">
        <article className="listing-main">
          {closed && (
            <div className="notice notice--closed" role="status">
              <strong>{t("closedTitle")}</strong> {t("closedText")}
            </div>
          )}
          {!listing.is_translated && (
            <p className="notice">{t("originalText", { lang: LANG_LABEL[listing.lang] })}</p>
          )}

          {listing.photos?.length > 0 && <PhotoGallery photos={listing.photos} alt={listing.title} />}

          <div className="listing-facts">
            <div className="listing-salary-big">
              {salary ?? price ?? <span className="job-card-nosalary">{tl("salaryNone")}</span>}
              {listing.salary_period && listing.salary_period !== "month" && listing.salary_monthly_min && (
                <small>{t("perMonth", { amount: formatEuro(listing.salary_monthly_min, locale) })}</small>
              )}
            </div>
            <ul className="tag-list">
              {listing.is_urgent && <li className="tag-pill tag-pill--accent">{tl("urgent")}</li>}
              {listing.source === "employer" && <li className="tag-pill">{t("directEmployer")}</li>}
              {listing.housing && <li className="tag-pill tag-pill--ok">{ts("housing")}</li>}
              {listing.no_language && <li className="tag-pill">{ts("no_language")}</li>}
              {listing.no_experience && <li className="tag-pill">{ts("no_experience")}</li>}
              {listing.schedule.map((s) => (
                <li key={s} className="tag-pill">
                  {ts(`schedule_${s}` as "schedule_full")}
                </li>
              ))}
              {listing.contract && <li className="tag-pill">{ts(`contract_${listing.contract}` as "contract_temporal")}</li>}
            </ul>
            {(facts.length > 0 || listing.attributes.length > 0) && (
              <dl className="attr-grid">
                {/* hiring details, then section tags, then the profession's own attributes */}
                {facts.map((f) => (
                  <div key={f.label}>
                    <dt>{f.label}</dt>
                    <dd>{f.value}</dd>
                  </div>
                ))}
                {[...listing.attributes].sort((a, b) => Number(a.group === "category") - Number(b.group === "category")).map((a) => (
                  <div key={a.key}>
                    <dt>{a.label}</dt>
                    <dd>{a.values.length ? a.values.join(", ") : "✓"}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>

          {[
            ["description", listing.description],
            ["requirements", listing.requirements],
            ["conditions", listing.conditions],
          ].map(([key, text]) =>
            text ? (
              <section key={key} className="listing-text">
                <h2>{t(key as "description")}</h2>
                <p>{text}</p>
              </section>
            ) : null,
          )}
        </article>

        <aside className="listing-aside" id="apply">
          {!closed && fromPerson && (
            <>
              <TrackListingView listingId={listing.id} />
              <SellerContact
                listingId={listing.id}
                signedIn={Boolean(account)}
                loginHref={localizedPath(locale, { type: "static", key: "login" })}
                chatsHref={`${localizedPath(locale, { type: "static", key: "account" })}?tab=chats`}
              />
            </>
          )}
          {!closed && !fromPerson && (
            <>
              <AppliedNotice id={listing.id} />
              <TrackListingView listingId={listing.id} />
              <ApplicationForm
                sectors={options.sectors}
                cities={options.cities}
                listingId={listing.id}
                questions={listing.questions ?? []}
                title={t("applyTitle")}
              />
              <a className="btn btn--telegram btn--lg btn--block" href={`${TELEGRAM_BOT.replace(/\/$/, "")}?start=l_${listing.id}`} rel="noopener">
                <Send size={16} aria-hidden /> {t("telegram")}
              </a>
              <p className="muted small">{t("applyText")}</p>
            </>
          )}
        </aside>
      </div>

      {listing.similar.length > 0 && (
        <section className="container similar">
          <h2>{t("similar")}</h2>
          <ul className="listing-grid">
            {listing.similar.map((s) => (
              <li key={s.id}>
                <ListingCard listing={s} locale={locale} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

