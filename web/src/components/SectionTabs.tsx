"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import type { Locale } from "@/i18n/routing";
import { type AppRoute, localizedPath } from "@/lib/routes";

// Jobs are the platform itself (the logo leads there) and "with housing" is a filter, so neither is a tab;
// the agency's services are shown as their two kinds: training and help with documents.
const TABS: { key: "drivers" | "training" | "documents" | "request"; route: AppRoute }[] = [
  { key: "drivers", route: { type: "agency", key: "drivers" } },
  { key: "training", route: { type: "list", key: "training" } },
  { key: "documents", route: { type: "list", key: "documents" } },
  { key: "request", route: { type: "static", key: "request" } },
];

export function SectionTabs({ locale }: { locale: Locale }) {
  const t = useTranslations("sections");
  const pathname = decodeURIComponent(usePathname());
  const hrefs = TABS.map((tab) => localizedPath(locale, tab.route));
  const matches = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  const activeIndex = hrefs.reduce<number>((acc, href, i) => (matches(href) && (acc < 0 || href.length > hrefs[acc].length) ? i : acc), -1);
  const nav = useRef<HTMLElement>(null);

  // on phones the tabs scroll sideways: bring the open one into view
  useEffect(() => {
    nav.current?.querySelector<HTMLElement>("[aria-current]")?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [activeIndex]);

  return (
    <nav ref={nav} className="section-tabs" aria-label="sections">
      {TABS.map(({ key }, i) => {
        const active = i === activeIndex;
        return (
          <Link key={key} href={hrefs[i]} className={active ? "tab tab--active" : "tab"} aria-current={active ? "page" : undefined}>
            {key === "documents" ? (
              <>
                {/* phones: the short name so all tabs fit in one row */}
                <span className="tab-long">{t(key)}</span>
                <span className="tab-short">{t("documentsShort")}</span>
              </>
            ) : (
              t(key)
            )}
          </Link>
        );
      })}
    </nav>
  );
}
