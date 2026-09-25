"use client";

import { Star } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { leaveReview } from "@/app/[locale]/review-actions";

/** Leaving a review: only works for somebody who has actually written to this seller. */
export function ReviewForm({ sellerId }: { sellerId: number }) {
  const t = useTranslations("seller");
  const [rating, setRating] = useState(5);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = String(new FormData(event.currentTarget).get("text") ?? "");
    setBusy(true);
    setError(null);
    const result = await leaveReview(sellerId, rating, text);
    setBusy(false);
    if (result.ok) setDone(true);
    else setError(result.error);
  }

  if (done) return <p className="notice notice--ok">{t("reviewSaved")}</p>;

  return (
    <form className="review-form" onSubmit={submit}>
      <h3>{t("leaveReview")}</h3>
      <div className="review-form__stars" role="radiogroup" aria-label={t("rating")}>
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={rating === star}
            aria-label={String(star)}
            className={star <= rating ? "star-button star-button--on" : "star-button"}
            onClick={() => setRating(star)}
          >
            <Star size={22} />
          </button>
        ))}
      </div>
      <label className="field">
        <span>{t("reviewText")}</span>
        <textarea name="text" rows={3} maxLength={1000} placeholder={t("reviewPlaceholder")} />
      </label>
      <button type="submit" className="btn btn--primary" disabled={busy}>
        {busy ? t("sending") : t("sendReview")}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {t.has(`errors.${error}` as "errors.generic")
            ? t(`errors.${error}` as "errors.generic")
            : t("errors.generic")}
        </p>
      )}
    </form>
  );
}
