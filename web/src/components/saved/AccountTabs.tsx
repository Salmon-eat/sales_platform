"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { ListingCard } from "@/components/home/ListingCard";
import { asLocale } from "@/i18n/routing";
import { useListingCards } from "@/lib/listing-cards";
import { localizedPath } from "@/lib/routes";
import { forgetApplied, useApplied, useFavorites } from "@/lib/saved";

export type AccountTab = "saved" | "applied";

export function AccountTabs({ initialTab }: { initialTab: AccountTab }) {
  const t = useTranslations("account");
  const locale = asLocale(useLocale());
  const [tab, setTab] = useState<AccountTab>(initialTab);
  const favorites = useFavorites();
  const applied = useApplied();

  const ids = tab === "saved" ? favorites.ids : applied.entries.map((e) => e.id);
  const { loading, error, cards } = useListingCards(ids, locale);
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
