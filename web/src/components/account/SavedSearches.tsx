"use client";

import { Bell, BellOff, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteSearch, setSearchNotify } from "@/app/[locale]/search-actions";
import { asLocale } from "@/i18n/routing";
import type { SavedSearch } from "@/lib/types";

/** The searches I asked to be told about, and the switch that stops the letters. */
export function SavedSearches({ initial }: { initial: SavedSearch[] }) {
  const t = useTranslations("savedSearch");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const [searches, setSearches] = useState(initial);
  const [busy, setBusy] = useState(false);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Europe/Madrid" });

  if (searches.length === 0) return null;

  async function toggle(id: number, notify: boolean) {
    setBusy(true);
    setSearches((current) => current.map((s) => (s.id === id ? { ...s, notify } : s)));
    await setSearchNotify(id, notify);
    setBusy(false);
    router.refresh();
  }

  async function remove(id: number) {
    setBusy(true);
    setSearches((current) => current.filter((s) => s.id !== id));
    await deleteSearch(id);
    setBusy(false);
    router.refresh();
  }

  return (
    <section className="saved-searches">
      <div className="home-block__head">
        <h2>{t("title")}</h2>
      </div>
      <ul className="saved-search-list">
        {searches.map((search) => (
          <li key={search.id} className="saved-search">
            <div>
              <strong>{search.title}</strong>
              <div className="muted small">
                {search.last_notified_at
                  ? t("lastTold", { date: date.format(new Date(search.last_notified_at)) })
                  : t("waitingForNew")}
              </div>
            </div>
            <button
              type="button"
              className={search.notify ? "btn btn--outline btn--sm" : "btn btn--ghost-dark btn--sm"}
              disabled={busy}
              onClick={() => toggle(search.id, !search.notify)}
            >
              {search.notify ? <Bell size={14} aria-hidden /> : <BellOff size={14} aria-hidden />}
              {search.notify ? t("on") : t("off")}
            </button>
            <button type="button" className="link-button" disabled={busy} onClick={() => remove(search.id)}>
              <Trash2 size={14} aria-hidden /> {t("remove")}
            </button>
          </li>
        ))}
      </ul>
      <p className="muted small">{t("hint")}</p>
    </section>
  );
}
