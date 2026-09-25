"use client";

import { Mail, Phone, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { track } from "@/lib/analytics";
import type { CompanyContact } from "@/lib/types";

/** The firm's phone is not printed into the page; it comes on a press, like a seller's. */
export function CompanyContactButton({ slug }: { slug: string }) {
  const t = useTranslations("companies");
  const [contact, setContact] = useState<CompanyContact | null>(null);
  const [busy, setBusy] = useState(false);

  async function show() {
    setBusy(true);
    try {
      const response = await fetch(`/v1/companies/${encodeURIComponent(slug)}/contact`);
      if (response.ok) {
        setContact((await response.json()) as CompanyContact);
        track("contact_click", { props: { kind: "company" } });
      }
    } finally {
      setBusy(false);
    }
  }

  if (!contact) {
    return (
      <button type="button" className="btn btn--primary btn--lg btn--block" onClick={show} disabled={busy}>
        <Phone size={16} aria-hidden /> {busy ? t("showing") : t("showContacts")}
      </button>
    );
  }

  return (
    <div className="company-contacts">
      {contact.phone && (
        <a href={`tel:${contact.phone.replace(/\s/g, "")}`} className="btn btn--primary btn--block">
          <Phone size={15} aria-hidden /> {contact.phone}
        </a>
      )}
      {contact.whatsapp && (
        <a className="btn btn--outline btn--block" href={`https://wa.me/${contact.whatsapp.replace(/\D/g, "")}`} rel="noopener">
          WhatsApp
        </a>
      )}
      {contact.telegram && (
        <a className="btn btn--outline btn--block" href={`https://t.me/${contact.telegram.replace(/^@/, "")}`} rel="noopener">
          <Send size={14} aria-hidden /> Telegram
        </a>
      )}
      {contact.email && (
        <a className="btn btn--outline btn--block" href={`mailto:${contact.email}`}>
          <Mail size={14} aria-hidden /> {contact.email}
        </a>
      )}
      {!contact.phone && !contact.whatsapp && !contact.telegram && !contact.email && (
        <p className="muted small">{t("noContacts")}</p>
      )}
    </div>
  );
}
