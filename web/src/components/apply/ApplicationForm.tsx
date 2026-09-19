"use client";

import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useId, useRef, useState } from "react";

import { Honeypot, honeypotValue, useHumanCheck } from "@/components/antibot";
import { PhoneInput } from "@/components/PhoneInput";
import { asLocale } from "@/i18n/routing";
import { attributionUtm, track } from "@/lib/analytics";
import { localizedPath } from "@/lib/routes";
import { forgetContact, markApplied, saveContact, useSavedContact } from "@/lib/saved";
import type { ApplicationOptions } from "@/lib/types";

const MESSENGERS = [
  ["phone", "messengerPhone"],
  ["telegram", "messengerTelegram"],
  ["whatsapp", "messengerWhatsapp"],
  ["viber", "messengerViber"],
] as const;
type Messenger = (typeof MESSENGERS)[number][0];

type Props = ApplicationOptions & {
  title: string;
  /** Preselected profession/sector, e.g. conductor-ce on the drivers page. */
  categoryId?: number;
  /** Application for a specific listing (card page). */
  listingId?: number;
  /** Placeholder of the comment, e.g. "what do you need" on the "didn't find a job" page. */
  commentPlaceholder?: string;
};

type State = { status: "idle" | "sending" | "sent"; error?: "phone" | "limit" | "captcha" | "generic" };

/** utm of this URL, else where the visitor came from earlier (a blogger's link a few days ago). */
function utmForApplication(): Record<string, string> {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = Object.fromEntries([...params].filter(([key]) => key.startsWith("utm_")));
  return Object.keys(fromUrl).length ? fromUrl : attributionUtm();
}

/** Application without registration: a manager calls back (spec §10). */
export function ApplicationForm({ sectors, cities, title, categoryId, listingId, commentPlaceholder }: Props) {
  const t = useTranslations("apply");
  const locale = asLocale(useLocale());
  const id = useId();
  const [state, setState] = useState<State>({ status: "idle" });
  // name and phone from the last application: the next one is one click (20 applications, one typing)
  const saved = useSavedContact();
  const [editing, setEditing] = useState(false);
  const quick = saved !== null && !editing;
  const [chosenMessenger, setMessenger] = useState<Messenger | null>(null);
  const [chosenInSpain, setInSpain] = useState<boolean | null | undefined>(undefined);
  const messenger = chosenMessenger ?? saved?.messenger ?? "phone";
  const inSpain = chosenInSpain === undefined ? (saved?.in_spain ?? null) : chosenInSpain;
  const opened = useRef(false);
  const human = useHumanCheck(locale);

  // the person started filling the form: sent vs. started shows where people give up
  function onStart() {
    if (opened.current) return;
    opened.current = true;
    track("apply_open", { listing_id: listingId });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (key: string) => String(form.get(key) ?? "").trim() || null;

    setState({ status: "sending" });
    try {
      const res = await fetch("/v1/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: text("name"),
          phone: text("phone"),
          messenger,
          lang: locale,
          listing_id: listingId ?? null,
          category_id: categoryId ?? (Number(form.get("category_id")) || null),
          location_slug: text("location_slug"),
          in_spain: inSpain,
          comment: text("comment"),
          consent: form.get("consent") === "on",
          utm: utmForApplication(),
          website: honeypotValue(form),
          captcha: human.token(),
        }),
      });
      human.reset();
      if (res.ok) {
        if (listingId) markApplied(listingId); // "applied" state on cards + history in the account
        saveContact({ name: text("name") ?? "", phone: text("phone") ?? "", messenger, in_spain: inSpain });
        track("apply_sent", { listing_id: listingId });
        setEditing(false);
        return setState({ status: "sent" });
      }
      if (res.status === 429) return setState({ status: "idle", error: "limit" });
      const body = await res.json().catch(() => null);
      if (body?.detail === "captcha") return setState({ status: "idle", error: "captcha" });
      const phoneError = body?.detail?.some?.((d: { loc?: string[] }) => d.loc?.includes("phone"));
      if (phoneError) setEditing(true); // show the phone field to fix it
      setState({ status: "idle", error: phoneError ? "phone" : "generic" });
    } catch {
      setState({ status: "idle", error: "generic" });
    }
  }

  if (state.status === "sent") {
    return (
      <div className="apply-card apply-success" role="status">
        <CheckCircle2 size={40} aria-hidden />
        <h3>{t("successTitle")}</h3>
        <p>{t("successText")}</p>
        <button type="button" className="btn btn--ghost-dark" onClick={() => setState({ status: "idle" })}>
          {t("again")}
        </button>
      </div>
    );
  }

  const sending = state.status === "sending";
  const field = (name: string) => `${id}-${name}`;

  return (
    <form className="apply-card apply-form" onSubmit={onSubmit} onFocus={onStart} noValidate={false}>
      <h3>{title}</h3>

      {quick ? (
        <div className="apply-saved">
          <input type="hidden" name="name" value={saved.name} />
          <input type="hidden" name="phone" value={saved.phone} />
          <span className="apply-saved__label">{t("savedFrom")}</span>
          <p className="apply-saved__who">
            <strong>{saved.name}</strong> · {saved.phone} · {t(MESSENGERS.find(([v]) => v === messenger)?.[1] ?? "messengerPhone")}
          </p>
          <div className="apply-saved__actions">
            <button type="button" className="link-button" onClick={() => setEditing(true)}>
              {t("savedChange")}
            </button>
            <button
              type="button"
              className="link-button"
              onClick={() => {
                forgetContact();
                setMessenger(null);
                setInSpain(undefined);
              }}
            >
              {t("savedNotMe")}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="field-row">
            <label className="field" htmlFor={field("name")}>
              <span>{t("name")}</span>
              <input
                id={field("name")}
                name="name"
                required
                minLength={2}
                maxLength={200}
                autoComplete="given-name"
                defaultValue={saved?.name}
                placeholder={t("namePlaceholder")}
              />
            </label>
            <label className="field" htmlFor={field("phone")}>
              <span>{t("phone")}</span>
              <PhoneInput
                key={saved?.phone ?? ""}
                id={field("phone")}
                name="phone"
                required
                autoComplete="tel"
                defaultValue={saved?.phone}
                placeholder={t("phonePlaceholder")}
                aria-invalid={state.error === "phone"}
              />
              {state.error === "phone" && <small className="field-error">{t("errorPhone")}</small>}
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
                  {t(label)}
                </button>
              ))}
            </div>
          </fieldset>
        </>
      )}

      <div className="field-row">
        {categoryId === undefined && listingId === undefined && sectors.length > 0 && (
          <label className="field" htmlFor={field("category")}>
            <span>{t("sector")}</span>
            <select id={field("category")} name="category_id" defaultValue="">
              <option value="">{t("sectorAny")}</option>
              {sectors.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {listingId === undefined && cities.length > 0 && (
          <label className="field" htmlFor={field("city")}>
            <span>{t("city")}</span>
            <select id={field("city")} name="location_slug" defaultValue="">
              <option value="">{t("cityAny")}</option>
              {cities.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {!quick && (
        <fieldset className="field">
          <legend>{t("inSpain")}</legend>
          <div className="choice-pills">
            {([true, false] as const).map((value) => (
              <button
                key={String(value)}
                type="button"
                className={inSpain === value ? "pill pill--active" : "pill"}
                aria-pressed={inSpain === value}
                onClick={() => setInSpain(inSpain === value ? null : value)}
              >
                {t(value ? "yes" : "no")}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <label className="field" htmlFor={field("comment")}>
        <span>
          {t("comment")} <small className="muted">({t("optional")})</small>
        </span>
        <textarea id={field("comment")} name="comment" rows={3} maxLength={1000} placeholder={commentPlaceholder ?? t("commentPlaceholder")} />
      </label>

      <label className="consent">
        <input type="checkbox" name="consent" required />
        <span>
          {t.rich("consent", {
            policy: (chunks) => (
              <Link href={localizedPath(locale, { type: "static", key: "privacy" })} target="_blank">
                {chunks}
              </Link>
            ),
          })}
        </span>
      </label>

      {!quick && <p className="apply-remember muted">{t("savedNote")}</p>}

      <Honeypot />
      {human.slot}

      {state.error && state.error !== "phone" && (
        <p className="form-error" role="alert">
          {t(state.error === "limit" ? "errorLimit" : state.error === "captcha" ? "errorCaptcha" : "errorGeneric")}
        </p>
      )}

      <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={sending}>
        {sending ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}
