"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AdCard } from "@/components/home/AdCard";
import { asLocale } from "@/i18n/routing";
import { clearViewed, useViewedIds } from "@/lib/saved";
import type { ListingCard } from "@/lib/types";

/** two rows of the grid: enough to find the ad again, not a whole archive */
const SHOWN = 14;

/**
 * "History": the ads this visitor opened, the latest first, so the one they liked yesterday is one click
 * away. It is read from this browser only; a visitor who has opened nothing sees no block at all.
 */
export function ViewedHistory() {
  const t = useTranslations("home");
  const locale = asLocale(useLocale());
  const ids = useViewedIds();
  // ask for a few more than shown: sold or closed ads drop out of the answer
  const key = ids.slice(0, SHOWN + 6).join(",");
  const [loaded, setLoaded] = useState<{ key: string; cards: ListingCard[] } | null>(null);

  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    fetch(`/v1/listings/cards?ids=${key}&lang=${locale}`, { signal: controller.signal })
      .then((res) => (res.ok ? (res.json() as Promise<ListingCard[]>) : []))
      .then((cards) => setLoaded({ key: `${locale}|${key}`, cards }))
      .catch(() => undefined);
    return () => controller.abort();
  }, [key, locale]);

  const cards = key && loaded?.key === `${locale}|${key}` ? loaded.cards.slice(0, SHOWN) : [];
  if (cards.length === 0) return null;

  return (
    <section className="home-block">
      <div className="home-block__head">
        <h2>{t("history")}</h2>
        <button type="button" className="home-block__link link-button" onClick={clearViewed}>
          {t("historyClear")}
        </button>
      </div>
      <ul className="ad-grid">
        {cards.map((item) => (
          <li key={item.id}>
            <AdCard listing={item} locale={locale} />
          </li>
        ))}
      </ul>
    </section>
  );
}
