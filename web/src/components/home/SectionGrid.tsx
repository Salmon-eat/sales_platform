import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import { prefixed } from "@/lib/routes";
import type { HomeSection } from "@/lib/types";

import { SectionArt, sectionHue } from "./SectionArt";

/** "All sections": what the whole site holds, at a glance. The picture is a look, not data. */
export async function SectionGrid({ locale, sections }: { locale: Locale; sections: HomeSection[] }) {
  const t = await getTranslations();

  return (
    <section className="home-block">
      <div className="home-block__head">
        <h2>{t("home.allSections")}</h2>
      </div>
      <ul className="section-grid">
        {sections.map((section) => (
          <li key={section.key}>
            <Link
              href={prefixed(locale, section.slug)}
              className="section-card"
              style={{ "--hue": sectionHue(section.key) } as React.CSSProperties}
            >
              <span className="section-card__art">
                <SectionArt sectionKey={section.key} />
              </span>
              <span className="section-card__body">
                <span className="section-card__title">{section.name}</span>
                <span className="section-card__count">{t("search.foundAds", { count: section.count })}</span>
                <span className="section-card__hints">{section.categories.map((c) => c.name).join(" · ")}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
