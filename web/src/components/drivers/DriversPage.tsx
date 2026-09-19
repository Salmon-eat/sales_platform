import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApplicationForm } from "@/components/apply/ApplicationForm";
import { Steps } from "@/components/apply/Steps";
import type { Locale } from "@/i18n/routing";
import { categoryPath, findCategory, getApplicationOptions, servicePath } from "@/lib/application-options";
import { type AppRoute, localizedPath, prefixed } from "@/lib/routes";
import { getListingStats, orFallback } from "@/lib/api";

// Agency service variants (licence B, C, CE): content, not data
const DOCUMENT_OPTIONS = 3;

type Direction = { code: string; title: string; accent?: string; text: string; meta: string; href: string };

/** Agency landing page for CE truck drivers (spec §6 "Сторінки агенції"). */
export async function DriversPage({ locale }: { locale: Locale }) {
  const t = await getTranslations("drivers");
  const tApply = await getTranslations("apply");
  const tPlaceholder = await getTranslations("placeholder");
  const { taxonomy, sectors, cities } = await getApplicationOptions(locale);
  const conductorCe = findCategory(taxonomy, "conductor-ce");
  const ceStats = await orFallback(getListingStats("conductor-ce"), { total: 0, today: 0 });

  const ceJobs = categoryPath(taxonomy, locale, "conductor-ce");
  const path = (route: AppRoute) => localizedPath(locale, route);
  const service = (esSlug: string) => {
    const to = servicePath(taxonomy, locale, esSlug);
    return to ? prefixed(locale, to) : path({ type: "list", key: "services" });
  };
  const directions: Direction[] = [
    {
      code: "01",
      title: t("d1Title"),
      accent: "CE",
      text: t("d1Text"),
      meta: t("d1Meta", { count: ceStats.total }),
      href: ceJobs ? prefixed(locale, ceJobs) : path({ type: "list", key: "work" }),
    },
    {
      code: "02",
      title: t("d2Title"),
      accent: "95",
      text: t("d2Text"),
      meta: t("d2Meta"),
      href: service("cap-95"),
    },
    {
      code: "03",
      title: t("d3Title"),
      text: t("d3Text"),
      meta: t("d3Meta", { count: DOCUMENT_OPTIONS }),
      href: service("canje-permiso"),
    },
  ];

  return (
    <>
      <section className="page-hero page-hero--dark">
        <div className="container">
          <nav className="breadcrumbs breadcrumbs--dark" aria-label="breadcrumbs">
            <Link href={path({ type: "home" })}>{tPlaceholder("home")}</Link>
            <span aria-hidden>›</span>
            <span>CE · 95</span>
          </nav>
          <h1>{t("title")}</h1>
          <p>{t("subtitle")}</p>
        </div>
      </section>

      <div className="container drivers">
        <section>
          <div className="section-head">
            <h2>{t("directionsTitle")}</h2>
            <span className="muted">{t("directionsCount", { count: directions.length })}</span>
          </div>
          <ul className="directions">
            {directions.map((d, i) => (
              <li key={d.code}>
                <Link href={d.href} className={i === 0 ? "direction direction--dark" : "direction"}>
                  <span className="direction-code">КМ {d.code}</span>
                  <span className="direction-title">
                    {d.title} {d.accent && <strong>{d.accent}</strong>}
                  </span>
                  <span className="direction-text">{d.text}</span>
                  <span className="direction-meta">
                    {d.meta}
                    <ArrowUpRight size={18} aria-hidden />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="section-title">{tApply("stepsTitle")}</h2>
          <Steps
            steps={[
              { icon: "request", title: tApply("step1Title"), text: tApply("step1Text") },
              { icon: "call", title: tApply("step2Title"), text: tApply("step2Text") },
              { icon: "documents", title: t("step3Title"), text: t("step3Text") },
              { icon: "truck", title: t("step4Title"), text: t("step4Text") },
            ]}
          />
        </section>

        <section className="apply apply--compact" id="apply">
          <div className="apply-intro">
            <span className="badge">{tApply("badge")}</span>
            <h2>{t("applyTitle")}</h2>
            <p className="apply-subtitle">{t("applySubtitle")}</p>
          </div>
          <ApplicationForm sectors={sectors} cities={cities} categoryId={conductorCe?.id} title={tApply("formTitle")} />
        </section>
      </div>
    </>
  );
}
