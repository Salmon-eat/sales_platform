"use client";

import { CheckCircle2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { useApplied } from "@/lib/saved";

/** On the card page: "you already applied on …" (from this browser's history). */
export function AppliedNotice({ id }: { id: number }) {
  const t = useTranslations("listingPage");
  const locale = useLocale();
  const entry = useApplied().get(id);
  if (!entry) return null;
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Europe/Madrid" }).format(new Date(entry.at));
  return (
    <p className="notice notice--ok applied-notice" role="status">
      <CheckCircle2 size={18} aria-hidden /> {t("appliedNotice", { date })}
    </p>
  );
}
