"use client";

import { Check, FileText, Send } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { applyWithResume } from "@/app/[locale]/resume-actions";
import { asLocale } from "@/i18n/routing";
import { markApplied } from "@/lib/saved";

type Props = {
  listingId: number;
  /** the candidate's headline, so they see what they are sending */
  title: string;
  hasFile: boolean;
  accountHref: string;
};

/** "Apply": one press for somebody whose CV is already in their account. */
export function QuickApply({ listingId, title, hasFile, accountHref }: Props) {
  const t = useTranslations("resume");
  const locale = asLocale(useLocale());
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<"sent" | "duplicate" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comment, setComment] = useState("");

  async function send() {
    setBusy(true);
    setError(null);
    const result = await applyWithResume(listingId, comment.trim() || undefined);
    setBusy(false);
    if (result.ok) {
      setDone(result.duplicate ? "duplicate" : "sent");
      markApplied(listingId);
    } else {
      setError(result.error);
    }
  }

  if (done) {
    return (
      <div className="quick-apply quick-apply--done">
        <Check size={20} aria-hidden />
        <div>
          <strong>{t(done === "duplicate" ? "alreadyApplied" : "applied")}</strong>
          <p className="muted small">{t("appliedText")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="quick-apply">
      <p className="quick-apply__who">
        <FileText size={15} aria-hidden /> {title}
        {hasFile && <span className="badge">{t("withFile")}</span>}
      </p>
      <label className="field">
        <span>{t("comment")}</span>
        <textarea
          rows={2}
          maxLength={1000}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder={t("commentPlaceholder")}
        />
      </label>
      <button type="button" className="btn btn--primary btn--lg btn--block" onClick={send} disabled={busy}>
        <Send size={16} aria-hidden /> {busy ? t("sending") : t("applyNow")}
      </button>
      <Link href={accountHref} className="link-button">
        {t("editResume")}
      </Link>
      {error && (
        <p className="form-error" role="alert">
          {t.has(`errors.${error}` as "errors.generic")
            ? t(`errors.${error}` as "errors.generic")
            : t("errors.generic")}
        </p>
      )}
    </div>
  );
}
