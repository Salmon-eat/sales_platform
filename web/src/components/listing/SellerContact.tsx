"use client";

import { MessageSquare, Phone, Send } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { writeToSeller } from "@/app/[locale]/chat-actions";
import { asLocale } from "@/i18n/routing";
import { track } from "@/lib/analytics";
import type { SellerContact as Contact } from "@/lib/types";

type Props = {
  listingId: number;
  signedIn: boolean;
  /** where to send a guest who wants to write to the seller */
  loginHref: string;
  chatsHref: string;
};

/**
 * How a buyer reaches the seller: the number is not in the page, it is asked for on a press, and the
 * message goes through the site so neither side has to give out an address to start talking.
 */
export function SellerContact({ listingId, signedIn, loginHref, chatsHref }: Props) {
  const t = useTranslations("seller");
  const locale = asLocale(useLocale());
  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function showPhone() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/v1/contact/${listingId}`);
      if (!response.ok) throw new Error(String(response.status));
      setContact((await response.json()) as Contact);
      track("contact_click", { listing_id: listingId, props: { kind: "phone" } });
    } catch {
      setError("contact_failed");
    } finally {
      setLoading(false);
    }
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = String(new FormData(event.currentTarget).get("text") ?? "").trim();
    if (!text) return;
    setBusy(true);
    setError(null);
    const result = await writeToSeller(listingId, text, locale);
    setBusy(false);
    if (result.ok) setSent(true);
    else setError(result.error);
  }

  const phone = contact?.phone ?? null;

  return (
    <div className="seller-box">
      <h2>{t("title")}</h2>

      {phone ? (
        <>
          <a href={`tel:${phone.replace(/\s/g, "")}`} className="btn btn--primary btn--lg btn--block">
            <Phone size={16} aria-hidden /> {phone}
          </a>
          {contact?.whatsapp && (
            <a
              className="btn btn--outline btn--block"
              href={`https://wa.me/${contact.whatsapp.replace(/\D/g, "")}`}
              rel="noopener"
            >
              WhatsApp
            </a>
          )}
          {contact?.telegram && (
            <a
              className="btn btn--outline btn--block"
              href={`https://t.me/${contact.telegram.replace(/^@/, "")}`}
              rel="noopener"
            >
              <Send size={15} aria-hidden /> Telegram
            </a>
          )}
        </>
      ) : (
        <button
          type="button"
          className="btn btn--primary btn--lg btn--block"
          onClick={showPhone}
          disabled={loading}
        >
          <Phone size={16} aria-hidden /> {loading ? t("showing") : t("showPhone")}
        </button>
      )}
      {contact && !contact.phone && <p className="muted small">{t("noPhone")}</p>}

      <div className="seller-box__chat">
        <h3>
          <MessageSquare size={15} aria-hidden /> {t("writeTitle")}
        </h3>
        {!signedIn ? (
          <>
            <p className="muted small">{t("signInToWrite")}</p>
            <Link href={loginHref} className="btn btn--outline btn--block">
              {t("signIn")}
            </Link>
          </>
        ) : sent ? (
          <>
            <p className="notice notice--ok">{t("sent")}</p>
            <Link href={chatsHref} className="btn btn--outline btn--block">
              {t("toChats")}
            </Link>
          </>
        ) : (
          <form onSubmit={send} className="seller-box__form">
            <label className="field">
              <span className="sr-only">{t("writeTitle")}</span>
              <textarea name="text" rows={3} maxLength={2000} required placeholder={t("placeholder")} />
            </label>
            <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
              {busy ? t("sending") : t("send")}
            </button>
          </form>
        )}
      </div>

      {error && (
        <p className="form-error" role="alert">
          {t.has(`errors.${error}` as "errors.generic")
            ? t(`errors.${error}` as "errors.generic")
            : t("errors.generic")}
        </p>
      )}
      <p className="muted small">{t("safety")}</p>
    </div>
  );
}
