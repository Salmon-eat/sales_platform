"use client";

import { Clock, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { clearSearches, forgetSearch, useRecentSearches } from "@/lib/saved";

type Props = {
  /** where the list opens: each search box places its dropdowns its own way */
  className?: string;
  /** called when a search is chosen, so the box closes its menu */
  onChoose?: () => void;
};

/**
 * "Recent searches": what this visitor searched for, shown under an empty search box the way every big
 * site does it. Each one opens the very page it led to; each can be forgotten, or all of them at once.
 * Nothing is shown to somebody who has not searched yet.
 */
export function RecentSearches({ className = "suggest", onChoose }: Props) {
  const t = useTranslations("search");
  const searches = useRecentSearches();
  if (searches.length === 0) return null;

  return (
    <div className={className} role="listbox" aria-label={t("recentTitle")}>
      <div className="suggest-group">
        <div className="suggest-title suggest-title--row">
          <span>{t("recentTitle")}</span>
          <button type="button" className="suggest-recent__clear" onClick={clearSearches}>
            {t("recentClear")}
          </button>
        </div>
        {searches.map((search) => (
          <div key={search.q} className="suggest-recent" role="option" aria-selected={false}>
            <Link href={search.href} className="suggest-recent__link" onClick={onChoose}>
              <Clock size={16} aria-hidden />
              <span>{search.q}</span>
            </Link>
            <button
              type="button"
              className="suggest-recent__forget"
              aria-label={t("recentForget", { q: search.q })}
              onClick={() => forgetSearch(search.q)}
            >
              <X size={15} aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
