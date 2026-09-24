import { LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { deleteAccount, signOut, updateProfile } from "@/app/[locale]/account-actions";
import { ConfirmSubmit } from "@/components/account/ConfirmSubmit";
import type { Locale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import type { Account } from "@/lib/types";

/** The bot that signs people in; it is also the one that can send them a notice. */
const LOGIN_BOT = process.env.NEXT_PUBLIC_TELEGRAM_LOGIN_BOT ?? "";

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
        <fieldset className="account-profile__notify">
          <legend>{t("notifyTitle")}</legend>
          <label className="check">
            <input type="checkbox" name="notify_email" defaultChecked={account.notify_email !== false} />
            <span>{t("notifyEmail")}</span>
          </label>
          <label className="check">
            <input
              type="checkbox"
              name="notify_telegram"
              defaultChecked={account.notify_telegram !== false}
              disabled={!account.has_telegram}
            />
            <span>{t("notifyTelegram")}</span>
          </label>
          <p className="muted small">
            {account.has_telegram ? t("notifyTelegramHint") : t("notifyTelegramOff")}{" "}
            {account.has_telegram && LOGIN_BOT && (
              <a href={`https://t.me/${LOGIN_BOT}`} rel="noopener">
                @{LOGIN_BOT}
              </a>
            )}
          </p>
        </fieldset>
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
