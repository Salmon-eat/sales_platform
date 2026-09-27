"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

export type Tab = { key: string; href: string; label: string };

/** The header tabs: the board's sections, in the order the API gives them. */
export function SectionTabs({ tabs }: { tabs: Tab[] }) {
  const pathname = decodeURIComponent(usePathname());
  const matches = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  // the longest match wins, should one tab's address ever start with another's
  const activeIndex = tabs.reduce<number>(
    (acc, tab, i) => (matches(tab.href) && (acc < 0 || tab.href.length > tabs[acc].href.length) ? i : acc),
    -1,
  );
  const nav = useRef<HTMLElement>(null);

  // on phones the tabs scroll sideways: bring the open one into view
  useEffect(() => {
    nav.current?.querySelector<HTMLElement>("[aria-current]")?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [activeIndex]);

  return (
    <nav ref={nav} className="section-tabs" aria-label="sections">
      {tabs.map((tab, i) => {
        const active = i === activeIndex;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            className={active ? "tab tab--active" : "tab"}
            aria-current={active ? "page" : undefined}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
