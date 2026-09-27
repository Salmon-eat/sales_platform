import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import type { HomeSection } from "@/lib/types";

import { SectionArt, sectionHue } from "./SectionArt";
import { SectionGridList } from "./SectionPicker";

/** "All sections": what the whole site holds, at a glance. The picture is a look, not data. */
export async function SectionGrid({ locale, sections }: { locale: Locale; sections: HomeSection[] }) {
  const t = await getTranslations();

  return (
    <section className="home-block">
      <div className="home-block__head">
        <h2>{t("home.allSections")}</h2>
      </div>
      {/* the cards are drawn here; the list around them opens a section's panel in place */}
      <SectionGridList
        cards={sections.map((section) => ({
          section: { key: section.key, slug: section.slug, name: section.name },
          style: { "--hue": sectionHue(section.key) } as React.CSSProperties,
          inside: (
            <>
              <span className="section-card__art">
                <SectionArt sectionKey={section.key} />
              </span>
              <span className="section-card__body">
                <span className="section-card__title">{section.name}</span>
                <span className="section-card__count">{t("search.foundAds", { count: section.count })}</span>
                <span className="section-card__hints">{section.categories.map((c) => c.name).join(" · ")}</span>
              </span>
            </>
          ),
        }))}
      />
    </section>
  );
}
