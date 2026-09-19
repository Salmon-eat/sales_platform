"use client";

import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { Honeypot, honeypotValue, useHumanCheck } from "@/components/antibot";
import { PhoneInput } from "@/components/PhoneInput";
import { asLocale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";

const MESSENGERS = [
  ["phone", "messengerPhone"],
  ["telegram", "messengerTelegram"],
  ["whatsapp", "messengerWhatsapp"],
  ["viber", "messengerViber"],
] as const;

/** "Publish a job" request (spec §1: employers send requests; managers publish the listing). */
export function EmployerRequestForm() {
  const t = useTranslations("publishForm");
  const tApply = useTranslations("apply");
  const locale = asLocale(useLocale());
  const [status, setStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<"phone" | "captcha" | "generic" | null>(null);
  const human = useHumanCheck(locale);
  const [messenger, setMessenger] = useState<(typeof MESSENGERS)[number][0]>("phone");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const value = (k: string) => String(form.get(k) ?? "").trim();
    setStatus("sending");
    setError(null);
    try {
      const res = await fetch("/v1/employer-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company: value("company"),
          contact_name: value("contact_name"),
          phone: value("phone"),
          email: value("email") || null,
          messenger,
          text: value("text"),
          lang: locale,
          consent: form.get("consent") === "on",
          website: honeypotValue(form),
          captcha: human.token(),
        }),
      });
      human.reset();
      if (res.ok) return setStatus("sent");
      const body = await res.json().catch(() => null);
      if (body?.detail === "captcha") setError("captcha");
      else setError(body?.detail?.some?.((d: { loc?: string[] }) => d.loc?.includes("phone")) ? "phone" : "generic");
    } catch {
      setError("generic");
    }
    setStatus("idle");
  }

  if (status === "sent") {
    return (
      <div className="apply-card apply-success" role="status">
        <CheckCircle2 size={40} aria-hidden />
        <h3>{t("successTitle")}</h3>
        <p>{t("successText")}</p>
      </div>
    );
  }

  return (
    <form className="apply-card apply-form" onSubmit={onSubmit}>
      <div className="field-row">
        <label className="field">
          <span>{t("company")}</span>
          <input name="company" required minLength={2} maxLength={200} autoComplete="organization" />
        </label>
        <label className="field">
          <span>{t("contactName")}</span>
          <input name="contact_name" required minLength={2} maxLength={200} autoComplete="name" />
        </label>
      </div>
      <div className="field-row">
        <label className="field">
          <span>{t("phone")}</span>
          <PhoneInput name="phone" required autoComplete="tel" placeholder="+34 612 345 678" aria-invalid={error === "phone"} />
          {error === "phone" && <small className="field-error">{t("errorPhone")}</small>}
        </label>
        <label className="field">
          <span>
            {t("email")} <small className="muted">({t("optional")})</small>
          </span>
          <input name="email" type="email" autoComplete="email" />
        </label>
      </div>
      <fieldset className="field">
        <legend>{t("messenger")}</legend>
        <div className="choice-pills">
          {MESSENGERS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={messenger === value ? "pill pill--active" : "pill"}
              aria-pressed={messenger === value}
              onClick={() => setMessenger(value)}
            >
              {tApply(label)}
            </button>
          ))}
        </div>
      </fieldset>
      <label className="field">
        <span>{t("text")}</span>
        <textarea name="text" rows={5} required minLength={10} maxLength={3000} placeholder={t("textPlaceholder")} />
      </label>
      <label className="consent">
        <input type="checkbox" name="consent" required />
        <span>
          {tApply.rich("consent", {
            policy: (chunks) => (
              <Link href={localizedPath(locale, { type: "static", key: "privacy" })} target="_blank">
                {chunks}
              </Link>
            ),
          })}
        </span>
      </label>
      <Honeypot />
      {human.slot}
      {(error === "generic" || error === "captcha") && (
        <p className="form-error" role="alert">
          {error === "captcha" ? tApply("errorCaptcha") : t("errorGeneric")}
        </p>
      )}
      <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={status === "sending"}>
        {status === "sending" ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}
