"use client";

import {
  CheckCircle2,
  MessageCircle,
  MessageSquareText,
  Phone,
  Send,
  SendHorizontal,
  X,
} from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { track } from "@/lib/analytics";
import { SiteChat, useChatUnread } from "./SiteChat";

type Props = {
  telegram?: string;
  /** phone numbers in any format; the links are built from the digits */
  whatsapp?: string;
  viber?: string;
  hours?: string;
  requestHref: string;
};

const digits = (phone: string) => phone.replace(/\D/g, "");

/** The mascot as the floating "write to a manager" button: a cat in a headset, a manager on the line.
 * Colours come from CSS (light: a cream cat on an orange disc; dark theme: an orange cat on a dark one). */
function CatHead() {
  return (
    <svg viewBox="-30 -30 60 60" className="contact-mascot__svg" aria-hidden>
      <circle r="28" className="contact-mascot__disc" />
      {/* ears: a curved outer edge, a softly rounded tip, a tuft of fur inside; the right one twitches */}
      <g>
        <path
          d="M-15.5 0 C-16.8 -8 -16 -15 -13.4 -19.6 Q-12.6 -20.8 -11.6 -19.9 C-8.6 -17 -5.6 -13.6 -2.8 -9.6 Z"
          className="contact-mascot__fur"
        />
        <path
          d="M-12.8 -4.5 C-13.6 -9.5 -13.2 -13.6 -12.2 -16.4 C-10 -14 -7.8 -11.4 -5.8 -8.8 Z"
          className="contact-mascot__inner"
        />
        <path d="M-12 -6 L-10.4 -10.4 M-10 -6.6 L-9.2 -10.8" className="contact-mascot__tuft" />
      </g>
      <g className="contact-mascot__ear">
        <path
          d="M15.5 0 C16.8 -8 16 -15 13.4 -19.6 Q12.6 -20.8 11.6 -19.9 C8.6 -17 5.6 -13.6 2.8 -9.6 Z"
          className="contact-mascot__fur"
        />
        <path
          d="M12.8 -4.5 C13.6 -9.5 13.2 -13.6 12.2 -16.4 C10 -14 7.8 -11.4 5.8 -8.8 Z"
          className="contact-mascot__inner"
        />
        <path d="M12 -6 L10.4 -10.4 M10 -6.6 L9.2 -10.8" className="contact-mascot__tuft" />
      </g>
      <ellipse cy="3" rx="15.5" ry="12.5" className="contact-mascot__fur" />
      {/* the headset: a band over the head, two cups, a microphone at the mouth */}
      <path d="M-16.5 1 C-17 -23 17 -23 16.5 1" className="contact-mascot__band" />
      <rect x="-20" y="-4" width="6.5" height="12" rx="3.2" className="contact-mascot__gear" />
      <rect x="13.5" y="-4" width="6.5" height="12" rx="3.2" className="contact-mascot__gear" />
      <path d="M-16 8 Q-14.5 14.5 -6.5 13.5" className="contact-mascot__boom" />
      <circle cx="-5.5" cy="13.4" r="2.3" className="contact-mascot__gear" />
      <g className="contact-mascot__eyes">
        <ellipse cx="-5.5" cy="1.5" rx="1.9" ry="2.6" fill="#16181d" />
        <ellipse cx="5.5" cy="1.5" rx="1.9" ry="2.6" fill="#16181d" />
        <circle cx="-4.9" cy="0.6" r="0.7" fill="#fff" />
        <circle cx="6.1" cy="0.6" r="0.7" fill="#fff" />
      </g>
      <circle cx="-9.5" cy="7" r="2" fill="#ff5d7a" opacity="0.3" />
      <circle cx="9.5" cy="7" r="2" fill="#ff5d7a" opacity="0.3" />
      <path d="M-1.7 6 L1.7 6 L0 7.9 Z" className="contact-mascot__inner" />
      <path
        d="M0 7.9 q-1.4 2.3 -3.3 1.2 M0 7.9 q1.4 2.3 3.3 1.2"
        stroke="#16181d"
        strokeWidth="1"
        strokeLinecap="round"
        fill="none"
      />    </svg>
  );
}

export function ContactWidget({
  telegram,
  whatsapp,
  viber,
  hours,
  requestHref,
}: Props) {
  const t = useTranslations("contactWidget");
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  // a manager replied while the window was closed
  const unread = useChatUnread(open && chat);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const hello = t("hello");
  const channels = [
    telegram && {
      key: "telegram",
      href: telegram,
      icon: Send,
      label: t("telegram"),
    },
    whatsapp && {
      key: "whatsapp",
      href: `https://wa.me/${digits(whatsapp)}?text=${encodeURIComponent(hello)}`,
      icon: MessageCircle,
      label: t("whatsapp"),
    },
    viber && {
      key: "viber",
      href: `viber://chat?number=%2B${digits(viber)}`,
      icon: Phone,
      label: t("viber"),
    },
  ].filter(Boolean) as {
    key: string;
    href: string;
    icon: typeof Send;
    label: string;
  }[];

  return (
    <div
      ref={box}
      className={`contact-widget${open ? " contact-widget--open" : ""}`}
    >
      {open && (
        <div className="contact-panel" role="dialog" aria-label={t("title")}>
          <button
            type="button"
            className="contact-panel__close"
            onClick={() => setOpen(false)}
            aria-label={t("close")}
          >
            <X size={18} />
          </button>
          <strong className="contact-panel__title">{t("title")}</strong>
          <p className="contact-panel__text">
            {hours ? t("subtitleHours", { hours }) : t("subtitle")}
          </p>
          {chat ? (
            <SiteChat onBack={() => setChat(false)} />
          ) : (
            <div className="contact-panel__list">
              <button
                type="button"
                className="contact-channel contact-channel--chat"
                onClick={() => {
                  track("contact_click", { props: { channel: "chat" } });
                  setChat(true);
                }}
              >
                <span className="contact-channel__icon">
                  <MessageSquareText size={18} aria-hidden />
                </span>
                {t("chat")}
              </button>
              {channels.map(({ key, href, icon: Icon, label }) => (
                <a
                  key={key}
                  href={href}
                  target="_blank"
                  rel="noopener"
                  className={`contact-channel contact-channel--${key}`}
                  onClick={() =>
                    track("contact_click", { props: { channel: key } })
                  }
                >
                  <span className="contact-channel__icon">
                    <Icon size={18} aria-hidden />
                  </span>
                  {label}
                </a>
              ))}
              <Link
                href={requestHref}
                className="contact-channel contact-channel--site"
                onClick={() => {
                  track("contact_click", { props: { channel: "site" } });
                  setOpen(false);
                }}
              >
                <span className="contact-channel__icon">
                  <MessageCircle size={18} aria-hidden />
                </span>
                {t("site")}
              </Link>
            </div>
          )}
        </div>
      )}
      <button
        type="button"
        className="contact-mascot"
        onClick={() => {
          setOpen((v) => !v);
          if (unread) setChat(true);
        }}
        aria-expanded={open}
        aria-label={t("open")}
      >
        {!open && (
          <span className="contact-mascot__hint">
            {t(unread ? "newReply" : "open")}
          </span>
        )}
        <CatHead />
        {unread && <span className="contact-mascot__dot" aria-hidden />}
      </button>
    </div>
  );
}
