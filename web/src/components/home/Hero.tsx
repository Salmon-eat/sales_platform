import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { SearchBox } from "@/components/search/SearchBox";
import type { Locale } from "@/i18n/routing";
import { categoryPath, findCategory } from "@/lib/application-options";
import { localizedPath, prefixed } from "@/lib/routes";
import type { ListingStats, Taxonomy } from "@/lib/types";

import { HeroStory } from "./HeroStory";

// spec §11: four popular queries under the search, linking to indexable tier-1 pages
const POPULAR = ["conductor-ce", "camarero", "limpieza-hogar"];

export async function Hero({
  locale,
  stats,
  taxonomy,
}: {
  locale: Locale;
  stats: ListingStats;
  taxonomy: Taxonomy;
}) {
  const t = await getTranslations("home");
  const tSections = await getTranslations("sections");
  const path = (key: "work" | "services" | "housingJobs") =>
    localizedPath(locale, { type: "list", key });

  const popular = [
    ...POPULAR.flatMap((slug) => {
      const category = findCategory(taxonomy, slug);
      const to = categoryPath(taxonomy, locale, slug);
      return category && to
        ? [{ name: category.name, href: prefixed(locale, to) }]
        : [];
    }),
    { name: tSections("housingJobs"), href: path("housingJobs") },
  ];

  return (
    <section className="hero">
      <div className="container hero-grid">
        <div className="hero-copy">
          <h1>
            {t("titleLine1")} {t("titleLine2")}
            <br />
            <span className="accent">{t("titleAccent")}</span>
          </h1>
          <p className="hero-stats">
            <span className="dot" aria-hidden />
            {t("stats", { total: stats.total, today: stats.today })}
          </p>
          <SearchBox
            sectionPaths={{ empleo: path("work"), servicios: path("services") }}
          />
          <p className="hero-popular">
            <span>{t("popular")}</span>
            {popular.map((p) => (
              <Link key={p.href} href={p.href}>
                {p.name}
              </Link>
            ))}
          </p>
        </div>
        <div className="plaza-tile">
          <HeroStory
            href={localizedPath(locale, { type: "static", key: "request" })}
            texts={{
              steps: ([1, 2, 3, 4] as const).map((n) => ({
                title: t(`story.step${n}Title`),
                text: t(`story.step${n}Text`),
              })),
              send: t("story.send"),
              minutes: t("story.minutes"),
              manager: t("story.manager"),
              bubble: [t("story.bubble1"), t("story.bubble2")],
              jobs: ([1, 2, 3] as const).map((n) => ({
                title: t(`story.job${n}Title`),
                salary: t(`story.job${n}Salary`),
              })),
              salary: t("story.salary"),
              amount: t("story.amount"),
              cta: t("story.cta"),
            }}
          />
        </div>
      </div>
    </section>
  );
}
