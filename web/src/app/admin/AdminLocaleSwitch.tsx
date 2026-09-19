"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { LOCALE_LABELS, LOCALES } from "@/i18n/routing";

import { setAdminLocale } from "./locale-actions";

/** UA / RU / EN / ES for the admin UI (each staff member picks their own). */
export function AdminLocaleSwitch() {
  const t = useTranslations("admin.shell");
  const current = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <div className="admin-locale" role="group" aria-label={t("language")} aria-busy={pending}>
      {LOCALES.map((locale) => (
        <button
          key={locale}
          type="button"
          className={locale === current ? "admin-locale-btn admin-locale-btn--active" : "admin-locale-btn"}
          aria-pressed={locale === current}
          onClick={() =>
            startTransition(async () => {
              await setAdminLocale(locale);
              router.refresh();
            })
          }
        >
          {LOCALE_LABELS[locale]}
        </button>
      ))}
    </div>
  );
}
