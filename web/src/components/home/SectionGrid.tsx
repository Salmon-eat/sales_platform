import {
  BadgeCheck,
  Bird,
  Briefcase,
  Building,
  Car,
  GraduationCap,
  Home,
  Megaphone,
  Package,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import { prefixed } from "@/lib/routes";
import type { HomeSection } from "@/lib/types";

/** Section key -> its icon. The names and counts come from the API, the icon is a look, not data. */
const ICONS: Record<string, typeof Home> = {
  empleo: Briefcase,
  inmobiliaria: Home,
  motor: Car,
  "servicios-sec": Wrench,
  servicios: BadgeCheck, // the agency's own services

  articulos: Package,
  animales: Bird,
  negocios: Building,
  "formacion-sec": GraduationCap,
  comunidad: Megaphone,
};

/** "All sections": what the whole site holds, at a glance. */
export async function SectionGrid({ locale, sections }: { locale: Locale; sections: HomeSection[] }) {
  const t = await getTranslations("home");
  const number = new Intl.NumberFormat(locale);

  return (
    <section className="home-block">
      <div className="home-block__head">
        <h2>{t("allSections")}</h2>
      </div>
      <ul className="section-grid">
        {sections.map((section) => {
          const Icon = ICONS[section.key] ?? Package;
          return (
            <li key={section.key}>
              <Link href={prefixed(locale, section.slug)} className="section-card">
                <span className="section-card__icon" aria-hidden>
                  <Icon size={18} />
                </span>
                <span className="section-card__title">
                  {section.name}
                  <span className="section-card__count">{number.format(section.count)}</span>
                </span>
                <span className="section-card__hints">
                  {section.categories.map((c) => c.name).join(" · ")}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
