import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import { prefixed } from "@/lib/routes";
import { sectionUi } from "@/lib/sections";
import type { HomeSection } from "@/lib/types";

import { SectionArt, sectionHue } from "./SectionArt";
import { SectionPickerLink } from "./SectionPicker";

/** "All sections": what the whole site holds, at a glance. The picture is a look, not data. */
export async function SectionGrid({ locale, sections }: { locale: Locale; sections: HomeSection[] }) {
  const t = await getTranslations();

  return (
    <section className="home-block">
      <div className="home-block__head">
        <h2>{t("home.allSections")}</h2>
      </div>
      <ul className="section-grid">
        {sections.map((section) => {
          const style = { "--hue": sectionHue(section.key) } as React.CSSProperties;
          const inside = (
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
          );
          return (
            <li key={section.key}>
              {/* a section with a "what are you looking for?" window opens it on this page */}
              {sectionUi(section.key).picker ? (
                <SectionPickerLink section={section} className="section-card" style={style}>
                  {inside}
                </SectionPickerLink>
              ) : (
                <Link href={prefixed(locale, section.slug)} className="section-card" style={style}>
                  {inside}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
