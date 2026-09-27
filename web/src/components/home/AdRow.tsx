"use client";

import { Camera } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { ago, useAdPrice } from "@/components/home/AdCard";
import { FavoriteButton } from "@/components/saved/FavoriteButton";
import type { Locale } from "@/i18n/routing";
import { prefixed } from "@/lib/routes";
import { useViewed } from "@/lib/saved";
import type { ListingCard as Card } from "@/lib/types";

/** enough to tell one car from the next (fuel, gearbox, year...); the rest is on the ad's page */
const MAX_TAGS = 5;

/**
 * An ad in a section's list, as the big classifieds show it: the photo on the left, the title with the
 * main facts under it, where and when at the bottom, the price on the right. Jobs keep their own card
 * (salary, "apply"); this one is for things, cars, flats, services.
 */
export function AdRow({ listing, locale, note }: { listing: Card; locale: Locale; note?: string }) {
  const t = useTranslations("listing");
  const viewed = useViewed().has(listing.id);
  const href = prefixed(locale, listing.path);
  const place = listing.location_scope === "spain_wide" ? t("spainWide") : listing.location?.name;
  const { money, per } = useAdPrice(listing, locale);
  const tags = (listing.tags ?? []).slice(0, MAX_TAGS);

  return (
    <article
      className={[
        "ad-row",
        viewed ? "ad-row--seen" : "",
        listing.highlighted ? "job-card--highlighted" : "",
        listing.promoted ? "job-card--top" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="ad-row__photo">
        {listing.photo ? (
          // the file is served by the site itself from /media
          <img src={listing.photo} alt="" loading="lazy" decoding="async" />
        ) : (
          <Camera size={24} aria-hidden />
        )}
      </div>
      <div className="ad-row__main">
        <h3 lang={listing.lang}>
          <Link href={href} className="listing-link">
            {listing.title}
          </Link>
          {listing.promoted && <span className="top-badge">{t("top")}</span>}
          {listing.is_urgent && <span className="urgent-badge">{t("urgent")}</span>}
          {!listing.is_translated && (
            <span className="lang-badge">{listing.lang === "uk" ? "UA" : listing.lang.toUpperCase()}</span>
          )}
        </h3>
        {tags.length > 0 && (
          <ul className="job-tags">
            {tags.map((tag) => (
              <li key={tag.key} className={`job-tag job-tag--${tag.kind}`}>
                {tag.label}
              </li>
            ))}
          </ul>
        )}
        <p className="ad-row__meta">
          {[place, ago(listing.published_at, locale)].filter(Boolean).join(" · ")}
        </p>
        {note && <p className="listing-note">{note}</p>}
      </div>
      <div className="ad-row__side">
        <p className="ad-row__price">
          {money}
          {per && <small>{per}</small>}
        </p>
        <FavoriteButton id={listing.id} />
      </div>
    </article>
  );
}
