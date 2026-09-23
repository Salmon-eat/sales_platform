import { LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { deleteAccount, signOut, updateProfile } from "@/app/[locale]/account-actions";
import { ConfirmSubmit } from "@/components/account/ConfirmSubmit";
import type { Locale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import type { Account } from "@/lib/types";

/** Top of the account page: who is signed in, their contacts, sign out, delete the account. */
export async function AccountPanel({ account, locale }: { account: Account | null; locale: Locale }) {
  const t = await getTranslations("account");

  if (!account) {
    return (
      <div className="account-guest">
        <UserRound size={28} aria-hidden />
        <div>
          <strong>{t("guestTitle")}</strong>
          <p className="muted small">{t("guestText")}</p>
        </div>
        <Link href={localizedPath(locale, { type: "static", key: "login" })} className="btn btn--primary">
          {t("signIn")}
        </Link>
      </div>
    );
  }

  return (
    <div className="account-profile">
      <div className="account-profile__head">
        <div>
          <strong>{account.name || account.email}</strong>
          <p className="muted small">{account.email}</p>
        </div>
        <form action={signOut}>
          <button type="submit" className="btn btn--ghost-dark btn--sm">
            <LogOut size={15} aria-hidden /> {t("signOut")}
          </button>
        </form>
      </div>

      <form action={updateProfile} className="account-profile__form">
        <label className="field">
          <span>{t("name")}</span>
          <input name="name" defaultValue={account.name ?? ""} maxLength={200} placeholder={t("namePlaceholder")} />
        </label>
        <label className="field">
          <span>{t("phone")}</span>
          <input name="phone" type="tel" defaultValue={account.phone ?? ""} placeholder="+34 612 345 678" />
        </label>
        <button type="submit" className="btn btn--primary btn--sm">
          {t("save")}
        </button>
      </form>

      <form action={deleteAccount} className="account-profile__danger">
        <ConfirmSubmit question={t("deleteConfirm")} className="link-button link-button--danger">
          {t("delete")}
        </ConfirmSubmit>
      </form>
    </div>
  );
}
