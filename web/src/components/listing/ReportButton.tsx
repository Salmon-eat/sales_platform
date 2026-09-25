"use client";

import { Flag } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { type ReportReason, reportListing } from "@/app/[locale]/report-actions";

const REASONS: ReportReason[] = [
  "fraud",
  "prohibited",
  "spam",
  "wrong_category",
  "duplicate",
  "offensive",
  "sold",
  "other",
];

/** "Report this ad": a small form, open to everyone, that puts the ad in front of a moderator. */
export function ReportButton({ listingId }: { listingId: number }) {
  const t = useTranslations("report");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    await reportListing(
      listingId,
      String(form.get("reason") ?? "other") as ReportReason,
      String(form.get("note") ?? ""),
    );
    setBusy(false);
    setSent(true);
  }

  if (sent) {
    return <p className="report-done muted small">{t("thanks")}</p>;
  }

  return (
    <div className="report">
      {!open ? (
        <button type="button" className="link-button report__open" onClick={() => setOpen(true)}>
          <Flag size={14} aria-hidden /> {t("open")}
        </button>
      ) : (
        <form className="report__form" onSubmit={submit}>
          <label className="field">
            <span>{t("why")}</span>
            <select name="reason" defaultValue="fraud">
              {REASONS.map((reason) => (
                <option key={reason} value={reason}>
                  {t(`reason_${reason}` as "reason_other")}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("note")}</span>
            <textarea name="note" rows={2} maxLength={500} placeholder={t("notePlaceholder")} />
          </label>
          <div className="report__actions">
            <button type="submit" className="btn btn--outline btn--sm" disabled={busy}>
              {busy ? t("sending") : t("send")}
            </button>
            <button type="button" className="link-button" onClick={() => setOpen(false)}>
              {t("cancel")}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
