import { Heart, Plus, Send, UserRound } from "lucide-react";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { asLocale } from "@/i18n/routing";
import { getAccount } from "@/lib/account";
import { getHome, orFallback } from "@/lib/api";
import { localizedPath, prefixed } from "@/lib/routes";

import { LocaleSwitcher } from "./LocaleSwitcher";
import { SavedCount } from "./saved/SavedCount";
import { Logo } from "./Logo";
import { SectionTabs, type Tab } from "./SectionTabs";
import { ThemeToggle } from "./ThemeToggle";

const TELEGRAM_URL = process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/";
/** The rest of the sections are one click away, in the grid on the home page. */
const MAX_SECTION_TABS = 6;

/** Light header (spec §11): logo, section links, language, saved, Telegram, "post a job". Search lives on the pages. */
export async function Header() {
  const locale = asLocale(await getLocale());
  const t = await getTranslations("header");
  const tSections = await getTranslations("sections");
  const account = await getAccount();
  // the sections come from the taxonomy, so a new one appears in the header on its own
  const home = await orFallback(getHome(locale), null);
  const tabs: Tab[] = [
    { key: "all", href: localizedPath(locale, { type: "search" }), label: tSections("all") },
    ...(home?.sections ?? []).slice(0, MAX_SECTION_TABS).map((section) => ({
      key: section.key,
      href: prefixed(locale, section.slug),
      label: section.name,
    })),
  ];

  return (
    <header className="site-header">
      <div className="container header-row">
        <Logo href={localizedPath(locale, { type: "home" })} />
        <SectionTabs tabs={tabs} />
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
          <Link
            href={localizedPath(locale, { type: "static", key: account ? "account" : "login" })}
            className="btn btn--outline header-account"
            title={account ? (account.name ?? account.email ?? t("account")) : t("signIn")}
          >
            <UserRound size={17} aria-hidden />
            <span>{account ? (account.name?.split(" ")[0] ?? t("account")) : t("signIn")}</span>
          </Link>
          <Link href={localizedPath(locale, { type: "static", key: "publish" })} className="btn btn--primary header-post">
            <Plus size={16} aria-hidden />
            <span>{t("post")}</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
