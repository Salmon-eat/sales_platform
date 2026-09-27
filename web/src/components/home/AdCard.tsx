"use client";

import { Camera } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useAdPrice, useCardBasics } from "@/components/home/card-basics";
import { FavoriteButton } from "@/components/saved/FavoriteButton";
import type { Locale } from "@/i18n/routing";
import { ago } from "@/lib/listing-format";
import type { ListingCard as Card } from "@/lib/types";

type Props = {
  listing: Card;
  locale: Locale;
  /** histories say whether the ad is still on offer ("Active" / "Inactive") */
  showStatus?: boolean;
};

/**
 * The card of the classifieds grid: photo, price, title, where and when. Jobs show their salary, an ad
 * without a price shows what it says instead ("free", "negotiable").
 */
export function AdCard({ listing, locale, showStatus = false }: Props) {
  const t = useTranslations("listing");
  const { href, place, viewed } = useCardBasics(listing, locale);
  const { money, per } = useAdPrice(listing, locale);
  const inactive = listing.active === false;

  return (
    <article
      className={[
        "ad-card",
        viewed ? "ad-card--seen" : "",
        // paid colour: a frame, never a different text colour, so it stays readable
        listing.highlighted ? "ad-card--highlighted" : "",
        listing.promoted && !inactive ? "ad-card--top" : "",
        inactive ? "ad-card--inactive" : "",
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
        {listing.promoted && !inactive && <span className="ad-card__top">{t("top")}</span>}
        <FavoriteButton id={listing.id} />
      </div>
      <div className="ad-card__body">
        {showStatus && (
          <span className={inactive ? "ad-status ad-status--off" : "ad-status ad-status--on"}>
            {t(inactive ? "statusInactive" : "statusActive")}
          </span>
        )}
        <p className="ad-card__price">
          {money}
          {per && <small>{per}</small>}
        </p>
        <h3>
          <Link href={href} className="listing-link">
            {listing.title}
          </Link>
        </h3>
        <p className="ad-card__meta">{[place, ago(listing.published_at, locale)].filter(Boolean).join(" · ")}</p>
      </div>
    </article>
  );
}
