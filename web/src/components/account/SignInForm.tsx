"use client";

import { Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  requestCode,
  signInWithCode,
  signInWithGoogle,
  signInWithTelegram,
} from "@/app/[locale]/account-actions";
import { asLocale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import { useFavorites } from "@/lib/saved";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
/** Username of the bot that only signs people in (never the working bot). */
const TELEGRAM_BOT = process.env.NEXT_PUBLIC_TELEGRAM_LOGIN_BOT ?? "";

type Step = "email" | "code";

declare global {
  interface Window {
    onTelegramAuth?: (user: Record<string, string | number>) => void;
  }
}

/** Sign in without a password: a code by email, or the Google button. */
export function SignInForm({ next }: { next?: string }) {
  const t = useTranslations("signIn");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const favorites = useFavorites();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const googleBox = useRef<HTMLDivElement>(null);
  const telegramBox = useRef<HTMLDivElement>(null);

  const done = () => router.replace(next || localizedPath(locale, { type: "static", key: "account" }));

  // Google's own button: it hands us a signed token, the API checks it
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !googleBox.current) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      const id = window.google?.accounts.id;
      if (!id || !googleBox.current) return;
      id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async ({ credential }: { credential: string }) => {
          setBusy(true);
          const result = await signInWithGoogle(credential, locale, favorites.ids);
          setBusy(false);
          if (result.ok) done();
          else setError(result.error ?? "generic");
        },
      });
      id.renderButton(googleBox.current, { theme: "outline", size: "large", width: 320, locale });
    };
    document.head.appendChild(script);
    return () => script.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale]);

  // Telegram's own widget: it signs the person's data with our login bot's token
  useEffect(() => {
    if (!TELEGRAM_BOT || !telegramBox.current) return;
    const box = telegramBox.current;
    window.onTelegramAuth = async (user: Record<string, string | number>) => {
      setBusy(true);
      const result = await signInWithTelegram(user, locale, favorites.ids);
      setBusy(false);
      if (result.ok) done();
      else setError(result.error ?? "generic");
    };
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", TELEGRAM_BOT);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "10");
    script.setAttribute("data-userpic", "false");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    box.appendChild(script);
    return () => {
      box.innerHTML = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale]);

  async function askCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const result = await requestCode(email.trim(), locale);
    setBusy(false);
    if (result.ok) setStep("code");
    else setError(result.error ?? "generic");
  }

  async function enterCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = String(new FormData(event.currentTarget).get("code") ?? "").trim();
    setBusy(true);
    setError(null);
    const result = await signInWithCode(email.trim(), code, locale, favorites.ids);
    setBusy(false);
    if (result.ok) done();
    else setError(result.error ?? "generic");
  }

  return (
    <div className="sign-in">
      <h1>{t("title")}</h1>
      <p className="muted">{t("subtitle")}</p>

      {(GOOGLE_CLIENT_ID || TELEGRAM_BOT) && (
        <>
          {GOOGLE_CLIENT_ID && <div ref={googleBox} className="sign-in__google" />}
          {TELEGRAM_BOT && <div ref={telegramBox} className="sign-in__telegram" />}
          <div className="sign-in__or">{t("or")}</div>
        </>
      )}

      {step === "email" ? (
        <form className="sign-in__form" onSubmit={askCode}>
          <label className="field">
            <span>{t("email")}</span>
            <input
              type="email"
              name="email"
              required
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t("emailPlaceholder")}
            />
          </label>
          <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={busy}>
            <Mail size={16} aria-hidden /> {busy ? t("sending") : t("sendCode")}
          </button>
        </form>
      ) : (
        <form className="sign-in__form" onSubmit={enterCode}>
          <p className="sign-in__sent">{t("sentTo", { email })}</p>
          <label className="field">
            <span>{t("code")}</span>
            <input
              name="code"
              required
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              autoFocus
              autoComplete="one-time-code"
              placeholder="123456"
            />
          </label>
          <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={busy}>
            {busy ? t("checking") : t("signIn")}
          </button>
          <button type="button" className="link-button" onClick={() => setStep("email")}>
            {t("changeEmail")}
          </button>
        </form>
      )}

      {error && (
        <p className="form-error" role="alert">
          {t(`errors.${error}` as "errors.generic")}
        </p>
      )}
      <p className="sign-in__legal muted small">{t("legal")}</p>
    </div>
  );
}
