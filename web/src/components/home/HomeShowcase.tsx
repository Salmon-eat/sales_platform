import { Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { AdSearch } from "@/components/home/AdSearch";
import { HeroScene } from "@/components/home/HeroScene";
import { SectionGrid } from "@/components/home/SectionGrid";
import { ViewedHistory } from "@/components/home/ViewedHistory";
import type { Locale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import type { Home } from "@/lib/types";

/** The home page of the classifieds: search, the sections, and the visitor's own history of opened ads.
 * Paid ads have no block of their own here: they come first in their section and in the search. */
export async function HomeShowcase({ locale, home }: { locale: Locale; home: Home }) {
  const t = await getTranslations("home");
  const number = new Intl.NumberFormat(locale);

  return (
    <>
      <section className="home-search">
        <HeroScene />
        <div className="container">
          <h1>{t("searchTitle")}</h1>
          <AdSearch sections={home.sections} />
          <p className="home-search__stats">
            <strong>{number.format(home.totals.listings)}</strong> {t("statsListings")}
            <span aria-hidden> · </span>
            <strong>{number.format(home.totals.today)}</strong> {t("statsToday")}
            <span aria-hidden> · </span>
            <strong>{home.totals.sections}</strong> {t("statsSections")}
          </p>
        </div>
      </section>

      <div className="container home-content">
        <SectionGrid locale={locale} sections={home.sections} />

        {/* the ads this visitor opened; nothing at all for somebody who has opened none */}
        <ViewedHistory />

        <section className="home-cta">
          <span className="home-cta__icon" aria-hidden>
            <Plus size={22} />
          </span>
          <div>
            <strong>{t("ctaTitle")}</strong>
            <p>{t("ctaText")}</p>
          </div>
          <Link href={localizedPath(locale, { type: "static", key: "publish" })} className="btn btn--primary btn--lg">
            {t("ctaButton")}
          </Link>
        </section>
      </div>
    </>
  );
}
