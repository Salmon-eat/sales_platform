import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { asLocale } from "@/i18n/routing";
import { localizedPath, type StaticKey } from "@/lib/routes";

import { Logo } from "./Logo";

const LINKS: StaticKey[] = ["publish", "faq", "contact", "privacy", "cookies", "legal"];

export async function Footer() {
  const locale = asLocale(await getLocale());
  const t = await getTranslations();

  return (
    <footer className="site-footer">
      <div className="container footer-row">
        <Logo href={localizedPath(locale, { type: "home" })} />
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
