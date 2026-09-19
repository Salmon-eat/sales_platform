"use client";

import { SendHorizontal } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { Honeypot, honeypotValue, useHumanCheck } from "@/components/antibot";
import { PhoneInput } from "@/components/PhoneInput";
import { attributionUtm, track } from "@/lib/analytics";
import { saveContact, useSavedContact } from "@/lib/saved";
import type { ChatMessage } from "@/lib/types";

const TOKEN_KEY = "bazarcito:chat";
const SEEN_KEY = "bazarcito:chat-seen";
const POLL_OPEN_MS = 8_000;
const POLL_CLOSED_MS = 60_000;

function storage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function store(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage blocked: the chat lives until reload */
  }
}

async function loadMessages(token: string): Promise<ChatMessage[] | null> {
  const res = await fetch(`/v1/chat/${token}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

const lastStaffId = (messages: ChatMessage[]) =>
  messages
    .filter((m) => m.author === "staff")
    .reduce((max, m) => Math.max(max, m.id), 0);

/**
 * A manager replied while the window was closed: the orange shows a dot. Checks once a minute and only
 * for people who have started a chat.
 */
export function useChatUnread(active: boolean): boolean {
  const [unread, setUnread] = useState(false);
  useEffect(() => {
    if (active) {
      setUnread(false);
      return;
    }
    let stopped = false;
    const check = async () => {
      const token = storage(TOKEN_KEY);
      if (!token) return;
      const messages = await loadMessages(token).catch(() => undefined);
      if (!stopped && messages)
        setUnread(lastStaffId(messages) > Number(storage(SEEN_KEY) ?? 0));
    };
    void check();
    const timer = setInterval(check, POLL_CLOSED_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [active]);
  return unread;
}

/**
 * "Write here": a conversation with the managers inside the orange window. The first message opens it
 * (the phone is optional); the browser keeps the token, so replies arrive here even days later.
 */
export function SiteChat({ onBack }: { onBack: () => void }) {
  const t = useTranslations("contactWidget");
  const tApply = useTranslations("apply");
  const locale = useLocale();
  const saved = useSavedContact();
  const [token, setToken] = useState<string | null>(() =>
    typeof window === "undefined" ? null : storage(TOKEN_KEY),
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<"idle" | "sending" | "error" | "phone" | "captcha">(
    "idle",
  );
  const human = useHumanCheck(locale);
  const list = useRef<HTMLOListElement>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    const next = await loadMessages(token).catch(() => undefined);
    if (next === null) {
      // the conversation was removed (e.g. data deletion on request): start afresh
      store(TOKEN_KEY, null);
      setToken(null);
      return;
    }
    if (next) {
      setMessages(next);
      store(SEEN_KEY, String(lastStaffId(next)));
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;
    void refresh();
    const timer = setInterval(refresh, POLL_OPEN_MS);
    return () => clearInterval(timer);
  }, [token, refresh]);

  useEffect(() => {
    list.current?.lastElementChild?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (key: string) => String(form.get(key) ?? "").trim();
    setState("sending");
    try {
      const res = await fetch("/v1/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: text("name"),
          phone: text("phone") || null,
          messenger: saved?.messenger ?? "phone",
          lang: locale,
          comment: text("message"),
          consent: form.get("consent") === "on",
          utm: attributionUtm(),
          channel: "chat",
          website: honeypotValue(form),
          captcha: human.token(),
        }),
      });
      human.reset();
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        if (body?.detail === "captcha") return setState("captcha");
        const phoneError = body?.detail?.some?.((d: { loc?: string[] }) =>
          d.loc?.includes("phone"),
        );
        return setState(phoneError ? "phone" : "error");
      }
      const created = (await res.json()) as { chat_token: string | null };
      if (text("phone")) {
        saveContact({
          name: text("name"),
          phone: text("phone"),
          messenger: saved?.messenger ?? "phone",
          in_spain: saved?.in_spain ?? null,
        });
      }
      track("apply_sent", { props: { channel: "chat" } });
      if (created.chat_token) {
        store(TOKEN_KEY, created.chat_token);
        setToken(created.chat_token);
      }
      setState("idle");
    } catch {
      setState("error");
    }
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formEl = event.currentTarget;
    const text = String(new FormData(formEl).get("message") ?? "").trim();
    if (!text || !token) return;
    setState("sending");
    try {
      const res = await fetch(`/v1/chat/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) return setState("error");
      setMessages(await res.json());
      formEl.reset();
      setState("idle");
    } catch {
      setState("error");
    }
  }

  if (!token) {
    return (
      <form className="contact-chat" onSubmit={start}>
        <textarea
          name="message"
          required
          minLength={2}
          maxLength={1000}
          rows={4}
          placeholder={t("messagePlaceholder")}
          autoFocus
        />
        <div className="contact-chat__row">
          <input
            name="name"
            required
            minLength={2}
            maxLength={200}
            defaultValue={saved?.name}
            placeholder={t("name")}
            autoComplete="given-name"
          />
          <PhoneInput
            key={saved?.phone ?? ""}
            name="phone"
            defaultValue={saved?.phone}
            placeholder={t("phoneOptional")}
            autoComplete="tel"
            aria-invalid={state === "phone"}
          />
        </div>
        <small className="muted">{t("phoneHint")}</small>
        {state === "phone" && (
          <small className="field-error">{t("errorPhone")}</small>
        )}
        <label className="consent">
          <input type="checkbox" name="consent" required />
          <span>{t("consent")}</span>
        </label>
        <Honeypot />
        {human.slot}
        {state === "error" && <p className="form-error">{t("error")}</p>}
        {state === "captcha" && <p className="form-error">{tApply("errorCaptcha")}</p>}
        <div className="contact-chat__actions">
          <button type="button" className="link-button" onClick={onBack}>
            {t("back")}
          </button>
          <button
            type="submit"
            className="btn btn--primary btn--sm"
            disabled={state === "sending"}
          >
            <SendHorizontal size={16} aria-hidden /> {t("send")}
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="contact-chat">
      <ol ref={list} className="contact-thread">
        {messages.map((m) => (
          <li
            key={m.id}
            className={`contact-bubble contact-bubble--${m.author}`}
          >
            {m.author === "staff" && (
              <span className="contact-bubble__who">{t("manager")}</span>
            )}
            {m.text}
          </li>
        ))}
        {messages.length > 0 && !messages.some((m) => m.author === "staff") && (
          <li className="contact-thread__note">{t("waiting")}</li>
        )}
      </ol>
      <form className="contact-compose" onSubmit={send}>
        <textarea
          name="message"
          required
          maxLength={1000}
          rows={2}
          placeholder={t("reply")}
        />
        <button
          type="submit"
          className="btn btn--primary btn--sm"
          disabled={state === "sending"}
          aria-label={t("send")}
        >
          <SendHorizontal size={16} aria-hidden />
        </button>
      </form>
      {state === "error" && <p className="form-error">{t("error")}</p>}
      <button type="button" className="link-button" onClick={onBack}>
        {t("back")}
      </button>
    </div>
  );
}
