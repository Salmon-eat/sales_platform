"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { actOnAd, deleteAd } from "@/app/[locale]/my-actions";
import { asLocale } from "@/i18n/routing";
import type { MyListingStatus } from "@/lib/types";

/** The buttons under one of my ads; what is possible depends on where the ad is in its life. */
export function MyAdActions({ id, status }: { id: number; status: MyListingStatus }) {
  const t = useTranslations("myAds");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function run(action: "submit" | "close" | "reopen" | "extend") {
    setBusy(true);
    await actOnAd(id, action, locale);
    setBusy(false);
    router.refresh();
  }

  async function remove() {
    if (!window.confirm(t("confirmDelete"))) return;
    setBusy(true);
    await deleteAd(id);
    setBusy(false);
    router.refresh();
  }

  const can = {
    submit: status === "draft" || status === "rejected" || status === "expired",
    extend: status === "active",
    close: status === "active" || status === "pending" || status === "draft",
    reopen: status === "closed" || status === "expired",
  };

  // the row of buttons belongs to the card; the "edit" link sits next to these
  return (
    <>
      {can.submit && (
        <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => run("submit")}>
          {t("send")}
        </button>
      )}
      {can.extend && (
        <button type="button" className="btn btn--outline btn--sm" disabled={busy} onClick={() => run("extend")}>
          {t("extend")}
        </button>
      )}
      {can.reopen && (
        <button type="button" className="btn btn--outline btn--sm" disabled={busy} onClick={() => run("reopen")}>
          {t("reopen")}
        </button>
      )}
      {can.close && (
        <button type="button" className="btn btn--ghost-dark btn--sm" disabled={busy} onClick={() => run("close")}>
          {t("close")}
        </button>
      )}
      <button type="button" className="link-button" disabled={busy} onClick={remove}>
        {t("delete")}
      </button>
    </>
  );
}
