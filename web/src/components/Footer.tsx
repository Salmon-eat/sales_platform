import { Send } from "lucide-react";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { asLocale } from "@/i18n/routing";
import { type AppRoute, localizedPath } from "@/lib/routes";
import { TELEGRAM_URL } from "@/lib/telegram";

import { Logo } from "./Logo";

type Item = { label: string; route: AppRoute };

/** Footer in columns: brand on the left, then the link groups, then where to follow us. */
export async function Footer() {
  const locale = asLocale(await getLocale());
  const t = await getTranslations();
  const page = (key: "publish" | "faq" | "contact" | "privacy" | "cookies" | "legal"): Item => ({
    label: t(`static.${key}`),
    route: { type: "static", key },
  });

  const columns: { title: string; items: Item[] }[] = [
    {
      // the agency's own pages: they are no longer header tabs, the header now shows the board's sections
      title: t("footer.agency"),
      items: [
        { label: t("sections.drivers"), route: { type: "agency", key: "drivers" } },
        { label: t("sections.training"), route: { type: "list", key: "training" } },
        { label: t("sections.documents"), route: { type: "list", key: "documents" } },
        { label: t("sections.request"), route: { type: "static", key: "request" } },
      ],
    },
    {
      title: t("footer.service"),
      items: [
        page("publish"),
        { label: t("companies.title"), route: { type: "companies" } },
        { label: t("blog.title"), route: { type: "blog" } },
      ],
    },
    { title: t("footer.help"), items: [page("faq"), page("contact")] },
    { title: t("footer.legal"), items: [page("privacy"), page("cookies"), page("legal")] },
  ];

  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-brand">
          <Logo href={localizedPath(locale, { type: "home" })} />
        </div>
        {columns.map((column) => (
          <nav key={column.title} className="footer-col" aria-label={column.title}>
            <h2>{column.title}</h2>
            <ul>
              {column.items.map((item) => (
                <li key={item.label}>
                  <Link href={localizedPath(locale, item.route)}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
        <div className="footer-col">
          <h2>{t("footer.follow")}</h2>
          <a href={TELEGRAM_URL} className="footer-social" aria-label={t("header.telegram")} rel="noopener">
            <Send size={20} aria-hidden />
          </a>
        </div>
      </div>
      <div className="container footer-bottom muted">{t("footer.rights", { year: new Date().getFullYear() })}</div>
    </footer>
  );
}
