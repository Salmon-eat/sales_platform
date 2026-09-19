"use client";

import { useCallback, useEffect, useRef } from "react";

/** Cloudflare Turnstile site key; empty = the check is off (the API has the matching secret). */
const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";
const SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

type Turnstile = {
  render: (el: HTMLElement, options: Record<string, unknown>) => string;
  reset: (id: string) => void;
  remove: (id: string) => void;
};

declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

let loading: Promise<void> | null = null;
function loadScript(): Promise<void> {
  if (window.turnstile) return Promise.resolve();
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new Error("turnstile"));
    };
    document.head.appendChild(script);
  });
  return loading;
}

/** Field people never see (off-screen, skipped by keyboard and screen readers); form bots fill it in. */
export function Honeypot() {
  return (
    <div className="hp-field" aria-hidden="true">
      <label>
        Website
        <input type="text" name="website" tabIndex={-1} autoComplete="off" defaultValue="" />
      </label>
    </div>
  );
}

/** The honeypot value of a submitted form. */
export const honeypotValue = (form: FormData) => String(form.get("website") ?? "") || null;

/**
 * The anti-bot check for a form. Most people never see it; a doubtful visitor gets a one-click box.
 * `slot` goes into the form; `token()` is sent with the request; `reset()` after each submit
 * (a token works once).
 */
export function useHumanCheck(lang: string) {
  const box = useRef<HTMLDivElement>(null);
  const widget = useRef<string | null>(null);
  const value = useRef<string | null>(null);

  useEffect(() => {
    if (!SITE_KEY || !box.current) return;
    const el = box.current;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !window.turnstile) return;
        widget.current = window.turnstile.render(el, {
          sitekey: SITE_KEY,
          language: lang === "ua" ? "uk" : lang,
          appearance: "interaction-only",
          callback: (token: string) => (value.current = token),
          "expired-callback": () => (value.current = null),
          "error-callback": () => (value.current = null),
        });
      })
      .catch(() => undefined); // blocked script: the API answers "captcha" and the form says so
    return () => {
      cancelled = true;
      if (widget.current) window.turnstile?.remove(widget.current);
      widget.current = null;
    };
  }, [lang]);

  const reset = useCallback(() => {
    value.current = null;
    if (widget.current) window.turnstile?.reset(widget.current);
  }, []);

  return {
    slot: SITE_KEY ? <div ref={box} className="human-check" /> : null,
    token: () => value.current,
    reset,
  };
}
