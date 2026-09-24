"use client";

import { ArrowLeft, Camera, Send } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { hideChat, openChat, replyInChat } from "@/app/[locale]/chat-actions";
import { asLocale } from "@/i18n/routing";
import { prefixed } from "@/lib/routes";
import type { Chat, ChatDetail } from "@/lib/types";

/** "My messages": the list of conversations on the left, the open one on the right. */
export function Chats({ initial }: { initial: Chat[] }) {
  const t = useTranslations("chats");
  const locale = asLocale(useLocale());
  const [list, setList] = useState(initial);
  const [open, setOpen] = useState<ChatDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const time = new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });

  useEffect(() => {
    setList(initial);
  }, [initial]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [open]);

  async function select(id: number) {
    setBusy(true);
    const chat = await openChat(id, locale);
    setBusy(false);
    if (!chat) return;
    setOpen(chat);
    setList((current) => current.map((item) => (item.id === id ? { ...item, unread: 0 } : item)));
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!open) return;
    const form = event.currentTarget;
    const text = String(new FormData(form).get("text") ?? "").trim();
    if (!text) return;
    setBusy(true);
    const result = await replyInChat(open.id, text, locale);
    setBusy(false);
    if (result.ok) {
      setOpen(result.chat);
      form.reset();
    }
  }

  async function remove(id: number) {
    await hideChat(id);
    setList((current) => current.filter((item) => item.id !== id));
    if (open?.id === id) setOpen(null);
  }

  if (list.length === 0) {
    return (
      <section className="chats">
        <h2>{t("title")}</h2>
        <p className="muted">{t("empty")}</p>
      </section>
    );
  }

  return (
    <section className="chats">
      <h2>{t("title")}</h2>
      <div className={open ? "chats__layout chats__layout--open" : "chats__layout"}>
        <ul className="chat-list">
          {list.map((chat) => (
            <li key={chat.id}>
              <button
                type="button"
                className={open?.id === chat.id ? "chat-row chat-row--on" : "chat-row"}
                onClick={() => select(chat.id)}
              >
                <span className="chat-row__photo">
                  {chat.listing_photo ? <img src={chat.listing_photo} alt="" /> : <Camera size={16} aria-hidden />}
                </span>
                <span className="chat-row__text">
                  <strong>{chat.other_name}</strong>
                  <small className="muted">{chat.listing_title}</small>
                  <small className="chat-row__last">{chat.last_text}</small>
                </span>
                {chat.unread > 0 && <span className="chat-row__unread">{chat.unread}</span>}
              </button>
            </li>
          ))}
        </ul>

        <div className="chat-thread">
          {!open ? (
            <p className="muted">{t("pick")}</p>
          ) : (
            <>
              <header className="chat-thread__head">
                <button type="button" className="link-button chat-thread__back" onClick={() => setOpen(null)}>
                  <ArrowLeft size={15} aria-hidden /> {t("back")}
                </button>
                <div>
                  <strong>{open.other_name}</strong>
                  <div className="muted small">
                    {open.listing_path ? (
                      <Link href={prefixed(locale, open.listing_path)} className="listing-link">
                        {open.listing_title}
                      </Link>
                    ) : (
                      open.listing_title
                    )}
                    {" · "}
                    {t(open.selling ? "asSeller" : "asBuyer")}
                  </div>
                </div>
                <button type="button" className="link-button" onClick={() => remove(open.id)}>
                  {t("hide")}
                </button>
              </header>

              <ol className="chat-messages">
                {open.messages.map((message) => (
                  <li key={message.id} className={message.mine ? "bubble bubble--mine" : "bubble"}>
                    <p>{message.text}</p>
                    <time dateTime={message.created_at}>{time.format(new Date(message.created_at))}</time>
                  </li>
                ))}
                <div ref={bottom} />
              </ol>

              <form className="chat-send" onSubmit={send}>
                <textarea name="text" rows={2} maxLength={2000} required placeholder={t("placeholder")} />
                <button type="submit" className="btn btn--primary" disabled={busy} aria-label={t("send")}>
                  <Send size={16} aria-hidden />
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
