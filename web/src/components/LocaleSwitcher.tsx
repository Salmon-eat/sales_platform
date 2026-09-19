"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import type { MouseEvent } from "react";

import { LOCALE_LABELS, LOCALES, type Locale, asLocale, localeFromPrefix } from "@/i18n/routing";
import { localizedPath, resolveSegments } from "@/lib/routes";

/** The equivalent page from the hreflang alternates rendered in <head> (API-resolved pages). */
function alternateFromHead(locale: Locale): string | null {
  const link = document.querySelector<HTMLLinkElement>(`link[rel="alternate"][hreflang="${locale}"]`);
  if (!link) return null;
  try {
    return new URL(link.href).pathname;
  } catch {
    return null;
  }
}

/** Leads to the equivalent page in another language (resolved by entity, not by swapping the prefix)
 * and keeps query filters. A page without a translation leads to the home page of that language. */
export function LocaleSwitcher() {
  const t = useTranslations("header");
  const current = asLocale(useLocale());
  const pathname = usePathname();
  const router = useRouter();
  const search = useSearchParams().toString();
  const query = search ? `?${search}` : "";

  const [, prefix, ...segments] = pathname.split("/");
  const resolved = localeFromPrefix(prefix) ? resolveSegments(current, segments.map(decodeURIComponent)) : null;
  const route = resolved?.route ?? { type: "home" as const };

  function onClick(event: MouseEvent<HTMLAnchorElement>, locale: Locale) {
    document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=31536000; samesite=lax`;
    if (resolved || event.metaKey || event.ctrlKey || event.shiftKey) return;
    const alternate = alternateFromHead(locale);
    if (!alternate) return;
    event.preventDefault();
    router.push(`${alternate}${query}`);
  }

  return (
    <nav className="locale-switcher" aria-label={t("language")}>
      {LOCALES.map((locale) => (
        <Link
          key={locale}
          href={`${localizedPath(locale, route)}${resolved ? query : ""}`}
          hrefLang={locale}
          aria-current={locale === current ? "true" : undefined}
          onClick={(event) => onClick(event, locale)}
        >
          {LOCALE_LABELS[locale]}
        </Link>
      ))}
    </nav>
  );
}
