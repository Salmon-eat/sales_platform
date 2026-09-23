import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { asLocale } from "@/i18n/routing";
import { type AppRoute, localizedPath, type StaticKey } from "@/lib/routes";

import { Logo } from "./Logo";

const LINKS: StaticKey[] = ["publish", "faq", "contact", "privacy", "cookies", "legal"];
/** The agency's own pages: they are no longer header tabs, the header now shows the board's sections. */
const AGENCY: { key: "drivers" | "training" | "documents" | "request"; route: AppRoute }[] = [
  { key: "drivers", route: { type: "agency", key: "drivers" } },
  { key: "training", route: { type: "list", key: "training" } },
  { key: "documents", route: { type: "list", key: "documents" } },
  { key: "request", route: { type: "static", key: "request" } },
];

export async function Footer() {
  const locale = asLocale(await getLocale());
  const t = await getTranslations();

  return (
    <footer className="site-footer">
      <div className="container footer-row">
        <Logo href={localizedPath(locale, { type: "home" })} />
        <nav className="footer-links" aria-label={t("footer.agency")}>
          {AGENCY.map(({ key, route }) => (
            <Link key={key} href={localizedPath(locale, route)}>
              {t(`sections.${key}`)}
            </Link>
          ))}
        </nav>
        <nav className="footer-links">
          {LINKS.map((key) => (
            <Link key={key} href={localizedPath(locale, { type: "static", key })}>
              {t(`static.${key}`)}
            </Link>
          ))}
        </nav>
        <span className="muted">{t("footer.rights", { year: new Date().getFullYear() })}</span>
      </div>
    </footer>
  );
}
