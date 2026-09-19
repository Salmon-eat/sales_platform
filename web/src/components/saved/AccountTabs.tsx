"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { ListingCard } from "@/components/home/ListingCard";
import { asLocale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import { forgetApplied, useApplied, useFavorites } from "@/lib/saved";
import type { ListingCard as Card } from "@/lib/types";

export type AccountTab = "saved" | "applied";

type Loaded = { key: string; cards: Map<number, Card> } | { key: string; error: true };

/** Cards for the ids kept in this browser; closed or removed listings come back missing. */
function useCards(ids: number[], lang: string) {
  const key = ids.join(",");
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    fetch(`/v1/listings/cards?ids=${key}&lang=${lang}`, { signal: controller.signal })
      .then((res) => (res.ok ? (res.json() as Promise<Card[]>) : Promise.reject(new Error(String(res.status)))))
      .then((cards) => setLoaded({ key: `${lang}|${key}`, cards: new Map(cards.map((c) => [c.id, c])) }))
      .catch((error: Error) => {
        if (error.name !== "AbortError") setLoaded({ key: `${lang}|${key}`, error: true });
      });
    return () => controller.abort();
  }, [key, lang]);

  // a result for an older list of ids is not shown (e.g. right after un-saving)
  const current = loaded && loaded.key === `${lang}|${key}` ? loaded : null;
  return {
    loading: Boolean(key) && !current,
    error: Boolean(current && "error" in current),
    cards: current && "cards" in current ? current.cards : new Map<number, Card>(),
  };
}

export function AccountTabs({ initialTab }: { initialTab: AccountTab }) {
  const t = useTranslations("account");
  const locale = asLocale(useLocale());
  const [tab, setTab] = useState<AccountTab>(initialTab);
  const favorites = useFavorites();
  const applied = useApplied();

  const ids = tab === "saved" ? favorites.ids : applied.entries.map((e) => e.id);
  const { loading, error, cards } = useCards(ids, locale);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Europe/Madrid" });

  function select(next: AccountTab) {
    setTab(next);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.replaceState(null, "", url); // bottom nav and reloads keep the tab
  }

  return (
    <div className="account">
      <div className="account-tabs" role="tablist">
        {(["saved", "applied"] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? "account-tab account-tab--active" : "account-tab"}
            onClick={() => select(key)}
          >
            {t(key === "saved" ? "tabSaved" : "tabApplied")}
            <span className="account-tab-count">{key === "saved" ? favorites.ids.length : applied.entries.length}</span>
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {ids.length === 0 ? (
          <div className="account-empty">
            <p>{t(tab === "saved" ? "emptySaved" : "emptyApplied")}</p>
            <Link href={localizedPath(locale, { type: "list", key: "work" })} className="btn btn--primary">
              {t("findJobs")}
            </Link>
          </div>
        ) : loading ? (
          <p className="muted">{t("loading")}</p>
        ) : error ? (
          <p className="notice notice--error">{t("error")}</p>
        ) : (
          <ul className="search-list">
            {ids.map((id) => {
              const card = cards.get(id);
              const entry = tab === "applied" ? applied.entries.find((e) => e.id === id) : undefined;
              return (
                <li key={id}>
                  {card ? (
                    <ListingCard listing={card} locale={locale} note={entry ? t("appliedAt", { date: date.format(new Date(entry.at)) }) : undefined} />
                  ) : (
                    <div className="account-gone">
                      <span>{t("gone")}</span>
                      <button
                        type="button"
                        className="btn btn--ghost-dark btn--sm"
                        onClick={() => (tab === "saved" ? favorites.toggle(id) : forgetApplied(id))}
                      >
                        {t("remove")}
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <p className="account-note muted">{t("localNote")}</p>
    </div>
  );
}
