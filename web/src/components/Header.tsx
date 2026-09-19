import { Heart, Plus, Send } from "lucide-react";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { asLocale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";

import { LocaleSwitcher } from "./LocaleSwitcher";
import { SavedCount } from "./saved/SavedCount";
import { Logo } from "./Logo";
import { SectionTabs } from "./SectionTabs";
import { ThemeToggle } from "./ThemeToggle";

const TELEGRAM_URL = process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/";

/** Light header (spec §11): logo, section links, language, saved, Telegram, "post a job". Search lives on the pages. */
export async function Header() {
  const locale = asLocale(await getLocale());
  const t = await getTranslations("header");

  return (
    <header className="site-header">
      <div className="container header-row">
        <Logo href={localizedPath(locale, { type: "home" })} />
        <SectionTabs locale={locale} />
        <div className="header-actions">
          <Suspense fallback={null}>
            <LocaleSwitcher />
          </Suspense>
          <ThemeToggle />
          <Link href={`${localizedPath(locale, { type: "static", key: "account" })}?tab=saved`} className="icon-button" aria-label={t("favorites")}>
            <Heart size={20} />
            <SavedCount />
          </Link>
          <a href={TELEGRAM_URL} className="icon-button" aria-label={t("telegram")} rel="noopener">
            <Send size={18} />
          </a>
          <Link href={localizedPath(locale, { type: "static", key: "publish" })} className="btn btn--primary header-post">
            <Plus size={16} aria-hidden />
            <span>{t("post")}</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
