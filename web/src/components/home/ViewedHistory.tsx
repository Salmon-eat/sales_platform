"use client";

import { useLocale, useTranslations } from "next-intl";

import { AdCard } from "@/components/home/AdCard";
import { asLocale } from "@/i18n/routing";
import { useListingCards } from "@/lib/listing-cards";
import { clearViewed, useViewedIds } from "@/lib/saved";

/** two rows of the grid: enough to find the ad again, not a whole archive */
const SHOWN = 14;

/**
 * "History": the ads this visitor opened, the latest first, each marked active or no longer on offer, so
 * the one they liked yesterday is one click away. Read from this browser only; a visitor who has opened
 * nothing sees no block at all.
 */
export function ViewedHistory() {
  const t = useTranslations("home");
  const locale = asLocale(useLocale());
  const ids = useViewedIds().slice(0, SHOWN);
  const { cards } = useListingCards(ids, locale, { withClosed: true });
  // in the order they were opened; drafts and removed ads never come back and are skipped
  const shown = ids.flatMap((id) => cards.get(id) ?? []);
  if (shown.length === 0) return null;

  return (
    <section className="home-block">
      <div className="home-block__head">
        <h2>{t("history")}</h2>
        <button type="button" className="home-block__link link-button" onClick={clearViewed}>
          {t("historyClear")}
        </button>
      </div>
      <ul className="ad-grid">
        {shown.map((item) => (
          <li key={item.id}>
            <AdCard listing={item} locale={locale} showStatus />
          </li>
        ))}
      </ul>
    </section>
  );
}
