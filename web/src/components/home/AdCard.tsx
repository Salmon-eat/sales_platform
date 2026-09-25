"use client";

import { Camera } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { FavoriteButton } from "@/components/saved/FavoriteButton";
import type { Locale } from "@/i18n/routing";
import { formatEuro, formatSalaryRange } from "@/lib/listing-format";
import { prefixed } from "@/lib/routes";
import { useViewed } from "@/lib/saved";
import type { ListingCard as Card } from "@/lib/types";

const PERIOD = { month: "perMonth", week: "perWeek", day: "perDay", hour: "perHour" } as const;

/** "2 h ago", "yesterday": coarse on purpose, so server and client render the same text. */
function ago(iso: string | null, locale: Locale): string {
  if (!iso) return "";
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (minutes < 60) return rtf.format(-Math.max(minutes, 1), "minute");
  if (minutes < 60 * 24) return rtf.format(-Math.round(minutes / 60), "hour");
  return rtf.format(-Math.round(minutes / (60 * 24)), "day");
}

/**
 * The card of the classifieds grid: photo, price, title, where and when. Jobs show their salary, an ad
 * without a price shows what it says instead ("free", "negotiable").
 */
export function AdCard({ listing, locale }: { listing: Card; locale: Locale }) {
  const t = useTranslations("listing");
  const viewed = useViewed().has(listing.id);
  const href = prefixed(locale, listing.path);
  const place = listing.location_scope === "spain_wide" ? t("spainWide") : listing.location?.name;

  const salary = formatSalaryRange(listing.salary_min, listing.salary_max, locale);
  const price = listing.price !== null && listing.price !== undefined ? formatEuro(listing.price, locale) : null;
  const period = listing.price_period ?? listing.salary_period ?? null;
  const money =
    listing.price_kind === "free"
      ? t("priceFree")
      : (salary ?? price ?? (listing.price_kind === "negotiable" ? t("priceAsk") : t("salaryNone")));

  return (
    <article
      className={[
        "ad-card",
        viewed ? "ad-card--seen" : "",
        // paid colour: a frame, never a different text colour, so it stays readable
        listing.highlighted ? "ad-card--highlighted" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="ad-card__photo">
        {listing.photo ? (
          // the file is served by the site itself from /media
          <img src={listing.photo} alt="" loading="lazy" decoding="async" />
        ) : (
          <Camera size={22} aria-hidden />
        )}
        {listing.promoted && <span className="ad-card__top">{t("top")}</span>}
        <FavoriteButton id={listing.id} />
      </div>
      <div className="ad-card__body">
        <p className="ad-card__price">
          {money}
          {period && (salary || price) && <small>{t(PERIOD[period])}</small>}
        </p>
        <h3>
          <Link href={href} className="listing-link">
            {listing.title}
          </Link>
        </h3>
        <p className="ad-card__meta">
          {[place, ago(listing.published_at, locale)].filter(Boolean).join(" · ")}
        </p>
      </div>
    </article>
  );
}
