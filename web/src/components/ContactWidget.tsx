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

/** The mascot's orange head as the floating "write to a manager" button. */
function OrangeHead() {
  return (
    <svg viewBox="-26 -34 52 58" className="contact-orange__svg" aria-hidden>
      <defs>
        <radialGradient id="contact-orange-shade" cx="0.35" cy="0.3" r="0.8">
          <stop offset="0.55" stopColor="#ff8a1f" stopOpacity="0" />
          <stop offset="1" stopColor="#d9620a" stopOpacity="0.55" />
        </radialGradient>
      </defs>
      <circle r="21" fill="#ff8a1f" />
      <circle r="21" fill="url(#contact-orange-shade)" />
      <ellipse
        cx="-8"
        cy="-10"
        rx="5"
        ry="3"
        fill="#fff"
        opacity="0.35"
        transform="rotate(-30 -8 -10)"
      />
      <path
        d="M0 -21 q1 -6 -1 -9"
        stroke="#6b4a2a"
        strokeWidth="2.2"
        strokeLinecap="round"
        fill="none"
      />
      <path
        className="contact-orange__leaf"
        d="M0 -25 q9 -9 17 -3 q-8 7 -17 3 z"
        fill="#3fae5a"
      />
      <g className="contact-orange__eyes">
        <ellipse cx="-7" cy="-2" rx="2.3" ry="3.3" fill="#16181d" />
        <ellipse cx="7" cy="-2" rx="2.3" ry="3.3" fill="#16181d" />
        <circle cx="-6.2" cy="-3.3" r="0.9" fill="#fff" />
        <circle cx="7.8" cy="-3.3" r="0.9" fill="#fff" />
      </g>
      <circle cx="-12" cy="6" r="3" fill="#ff5d7a" opacity="0.45" />
      <circle cx="12" cy="6" r="3" fill="#ff5d7a" opacity="0.45" />
      <path d="M-5 7 q5 6 10 0 z" fill="#7a2a12" />
    </svg>
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
        className="contact-orange"
        onClick={() => {
          setOpen((v) => !v);
          if (unread) setChat(true);
        }}
        aria-expanded={open}
        aria-label={t("open")}
      >
        {!open && (
          <span className="contact-orange__hint">
            {t(unread ? "newReply" : "open")}
          </span>
        )}
        <OrangeHead />
        {unread && <span className="contact-orange__dot" aria-hidden />}
      </button>
    </div>
  );
}
