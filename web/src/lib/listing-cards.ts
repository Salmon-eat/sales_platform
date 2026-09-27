"use client";

import { useEffect, useState } from "react";

import type { ListingCard } from "./types";

type Loaded = { key: string; cards: Map<number, ListingCard> } | { key: string; error: true };

/**
 * Cards for ids kept in this browser (saved, applied, viewed), in the page language. Ads that are gone
 * come back missing; with `withClosed` the ones that were once public come back too, marked inactive.
 * A result for an older list of ids is never shown (right after un-saving, say).
 */
export function useListingCards(ids: number[], lang: string, { withClosed = false } = {}) {
  const key = ids.join(",");
  const tag = `${lang}|${withClosed}|${key}`;
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    const extra = withClosed ? "&with_closed=true" : "";
    fetch(`/v1/listings/cards?ids=${key}&lang=${lang}${extra}`, { signal: controller.signal })
      .then((res) => (res.ok ? (res.json() as Promise<ListingCard[]>) : Promise.reject(new Error(String(res.status)))))
      .then((cards) => setLoaded({ key: tag, cards: new Map(cards.map((c) => [c.id, c])) }))
      .catch((error: Error) => {
        if (error.name !== "AbortError") setLoaded({ key: tag, error: true });
      });
    return () => controller.abort();
  }, [key, lang, withClosed, tag]);

  const current = loaded && loaded.key === tag ? loaded : null;
  return {
    loading: Boolean(key) && !current,
    error: Boolean(current && "error" in current),
    cards: current && "cards" in current ? current.cards : new Map<number, ListingCard>(),
  };
}
