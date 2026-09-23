"use client";

import { CheckCircle2, Paperclip } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useId, useRef, useState } from "react";

import { Honeypot, honeypotValue, useHumanCheck } from "@/components/antibot";
import { PhoneInput } from "@/components/PhoneInput";
import { asLocale } from "@/i18n/routing";
import { attributionUtm, track } from "@/lib/analytics";
import { localizedPath } from "@/lib/routes";
import { forgetContact, markApplied, saveContact, useSavedContact } from "@/lib/saved";
import type { ApplicationOptions, ListingQuestion } from "@/lib/types";

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
  /** The listing's optional questions (the manager chose them); the candidate may skip them. */
  questions?: ListingQuestion[];
};

type State = {
  status: "idle" | "sending" | "sent";
  error?: "phone" | "limit" | "captcha" | "generic";
  /** the application went through but the CV did not */
  cvFailed?: boolean;
};

const CV_MAX = 5 * 1024 * 1024;
const CV_TYPES = /\.(pdf|docx?|jpe?g|png)$/i;

/** The CV goes after the application, with the one-time key the answer gave. */
async function uploadCv(token: string, file: File): Promise<boolean> {
  try {
    const res = await fetch(`/v1/applications/cv/${token}`, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/octet-stream", "X-File-Name": encodeURIComponent(file.name) },
      body: file,
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** utm of this URL, else where the visitor came from earlier (a blogger's link a few days ago). */
function utmForApplication(): Record<string, string> {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = Object.fromEntries([...params].filter(([key]) => key.startsWith("utm_")));
  return Object.keys(fromUrl).length ? fromUrl : attributionUtm();
}

/** Application without registration: a manager calls back (spec §10). */
export function ApplicationForm({ sectors, cities, title, categoryId, listingId, commentPlaceholder, questions = [] }: Props) {
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
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [cvError, setCvError] = useState<"type" | "size" | null>(null);

  function pickCv(file: File | null) {
    setCvError(null);
    if (!file) return setCvFile(null);
    if (!CV_TYPES.test(file.name)) return setCvError("type");
    if (file.size > CV_MAX) return setCvError("size");
    setCvFile(file);
  }

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
          questions: answers,
          website: honeypotValue(form),
          captcha: human.token(),
        }),
      });
      human.reset();
      if (res.ok) {
        const created = (await res.json().catch(() => ({}))) as { cv_token?: string | null };
        const cvFailed = cvFile ? !(created.cv_token && (await uploadCv(created.cv_token, cvFile))) : false;
        if (listingId) markApplied(listingId); // "applied" state on cards + history in the account
        saveContact({ name: text("name") ?? "", phone: text("phone") ?? "", messenger, in_spain: inSpain });
        track("apply_sent", { listing_id: listingId });
        setEditing(false);
        setCvFile(null);
        return setState({ status: "sent", cvFailed });
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
        {state.cvFailed && <p className="notice notice--warn">{t("cvFailed")}</p>}
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

      {/* the manager's questions for this job: a click each, all optional */}
      {questions.length > 0 && (
        <div className="apply-questions">
          <p className="apply-questions__title">
            {t("questionsTitle")} <small className="muted">({t("optional")})</small>
          </p>
          {questions.map((q) => (
            <fieldset key={q.key} className="field">
              <legend>{q.text}</legend>
              <div className="choice-pills">
                {q.options.map((o) => {
                  const on = answers[q.key] === o.value;
                  return (
                    <button
                      key={o.value}
                      type="button"
                      className={on ? "pill pill--active" : "pill"}
                      aria-pressed={on}
                      onClick={() =>
                        setAnswers((prev) => {
                          const next = { ...prev };
                          if (on) delete next[q.key];
                          else next[q.key] = o.value;
                          return next;
                        })
                      }
                    >
                      {o.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          ))}
        </div>
      )}

      {/* a CV if the person has one: never required */}
      <div className="apply-cv">
        {cvFile ? (
          <p className="apply-cv__file">
            <Paperclip size={15} aria-hidden /> <span>{cvFile.name}</span>
            <button type="button" className="link-button" onClick={() => pickCv(null)}>
              {t("cvRemove")}
            </button>
          </p>
        ) : (
          <label className="apply-cv__pick">
            <Paperclip size={15} aria-hidden /> {t("cvAdd")} <small className="muted">({t("optional")})</small>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              onChange={(e) => {
                pickCv(e.target.files?.[0] ?? null);
                e.target.value = "";
              }}
            />
          </label>
        )}
        {cvError ? (
          <small className="field-error">{t(cvError === "type" ? "cvErrorType" : "cvErrorSize")}</small>
        ) : (
          !cvFile && <small className="muted">{t("cvHint")}</small>
        )}
      </div>

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
