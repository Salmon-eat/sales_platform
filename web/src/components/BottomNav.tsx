"use client";

import { Heart, House, type LucideIcon, Search, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

import { asLocale } from "@/i18n/routing";
import { type AppRoute, localizedPath } from "@/lib/routes";

import { SavedCount } from "./saved/SavedCount";

type Item = { key: "home" | "search" | "saved" | "account"; route: AppRoute; query?: string; icon: LucideIcon };

const ITEMS: Item[] = [
  { key: "home", route: { type: "home" }, icon: House },
  { key: "search", route: { type: "list", key: "work" }, icon: Search },
  { key: "saved", route: { type: "static", key: "account" }, query: "?tab=saved", icon: Heart },
  { key: "account", route: { type: "static", key: "account" }, query: "?tab=applied", icon: UserRound },
];

/** Mobile bottom navigation (spec §11): Home, Search, Saved, Account. Hidden on desktop by CSS. */
export function BottomNav() {
  const t = useTranslations("nav");
  const locale = asLocale(useLocale());
  const pathname = decodeURIComponent(usePathname());

  return (
    <nav className="bottom-nav" aria-label={t("home")}>
      {ITEMS.map(({ key, route, query = "", icon: Icon }) => {
        const href = localizedPath(locale, route);
        // the account page holds both "saved" and "applications": highlight the account item there
        const active = route.type === "home" ? pathname === href : key !== "saved" && pathname.startsWith(href);
        return (
          <Link
            key={key}
            href={`${href}${query}`}
            className={active ? "bottom-nav-item bottom-nav-item--active" : "bottom-nav-item"}
            aria-current={active ? "page" : undefined}
          >
            <span className="bottom-nav-icon">
              <Icon size={21} aria-hidden />
              {key === "saved" && <SavedCount />}
            </span>
            <span>{t(key)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
