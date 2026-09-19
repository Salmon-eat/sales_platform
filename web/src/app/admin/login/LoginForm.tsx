"use client";

import Script from "next/script";
import { useLocale, useTranslations } from "next-intl";
import { useActionState, useCallback, useEffect, useRef, useState, useTransition } from "react";

import { devLogin, googleLogin, type LoginState } from "../actions";
import { AdminLocaleSwitch } from "../AdminLocaleSwitch";

type GoogleId = {
  initialize: (options: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: string }) => void;
  renderButton: (el: HTMLElement, options: Record<string, string | number>) => void;
};
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } };
  }
}

type Props = { googleClientId: string | null; devLogin: boolean };

/** One "Sign in with Google" button, no registration or password recovery (admin spec §1). */
export function LoginForm({ googleClientId, devLogin: devEnabled }: Props) {
  const t = useTranslations("admin.login");
  const locale = useLocale();
  const [googleState, setGoogleState] = useState<LoginState>({});
  const [pending, startTransition] = useTransition();
  const [devState, devAction, devPending] = useActionState<LoginState, FormData>(devLogin, {});
  const [scriptReady, setScriptReady] = useState(false);
  const button = useRef<HTMLDivElement>(null);

  const onCredential = useCallback(({ credential }: { credential: string }) => {
    startTransition(async () => setGoogleState(await googleLogin(credential)));
  }, []);

  useEffect(() => {
    const google = window.google?.accounts.id;
    if (!scriptReady || !google || !googleClientId || !button.current) return;
    google.initialize({ client_id: googleClientId, callback: onCredential });
    google.renderButton(button.current, { theme: "outline", size: "large", text: "signin_with", locale, width: 300 });
  }, [scriptReady, googleClientId, onCredential, locale]);

  const error = googleState.error ?? devState.error;

  return (
    <div className="login-screen">
      {googleClientId && (
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={() => setScriptReady(true)} />
      )}
      <div className="login">
        <span className="logo">
          bazar<span>cito</span>
        </span>
        <h1>{t("title")}</h1>
        {googleClientId ? (
          <div className="login-google" ref={button} aria-busy={pending} />
        ) : (
          !devEnabled && <p className="login-hint">{t("unavailable")}</p>
        )}
        {pending && <p className="login-hint">{t("checking")}</p>}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        {devEnabled && (
          <form action={devAction} className="login-dev">
            <input name="email" type="email" placeholder={t("email")} autoComplete="username" required />
            <button type="submit" className="btn btn--ghost" disabled={devPending}>
              {devPending ? t("signingIn") : t("byEmail")}
            </button>
          </form>
        )}
        <AdminLocaleSwitch />
      </div>
    </div>
  );
}
