"use client";

import { BellPlus, Check } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { saveSearch } from "@/app/[locale]/search-actions";
import { asLocale } from "@/i18n/routing";

type Props = {
  title: string;
  sectionKey?: string | null;
  categorySlug?: string | null;
  locationSlug?: string | null;
  params?: Record<string, string>;
  signedIn: boolean;
  loginHref: string;
};

/** "Tell me when something new turns up": the search as it stands, kept for later. */
export function SaveSearchButton({
  title,
  sectionKey,
  categorySlug,
  locationSlug,
  params,
  signedIn,
  loginHref,
}: Props) {
  const t = useTranslations("savedSearch");
  const locale = asLocale(useLocale());
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!signedIn) {
    return (
      <Link href={loginHref} className="link-button save-search">
        <BellPlus size={15} aria-hidden /> {t("signInToSave")}
      </Link>
    );
  }

  if (saved) {
    return (
      <span className="save-search save-search--done">
        <Check size={15} aria-hidden /> {t("saved")}
      </span>
    );
  }

  async function save() {
    setBusy(true);
    setError(null);
    const result = await saveSearch(
      {
        title,
        section_key: sectionKey,
        category_slug: categorySlug,
        location_slug: locationSlug,
        params,
      },
      locale,
    );
    setBusy(false);
    if (result.ok) setSaved(true);
    else setError(result.error);
  }

  return (
    <>
      <button type="button" className="link-button save-search" disabled={busy} onClick={save}>
        <BellPlus size={15} aria-hidden /> {busy ? t("saving") : t("save")}
      </button>
      {error && (
        <span className="form-error">
          {t.has(`errors.${error}` as "errors.generic")
            ? t(`errors.${error}` as "errors.generic")
            : t("errors.generic")}
        </span>
      )}
    </>
  );
}
