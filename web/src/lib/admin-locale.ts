import "server-only";

import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";

import { isLocale, type Locale } from "@/i18n/routing";

import type { AdminMessages } from "../../messages/admin";

/** The admin UI language is chosen by each staff member, independently of the site language. */
export const ADMIN_LOCALE_COOKIE = "admin_locale";
export const DEFAULT_ADMIN_LOCALE: Locale = "uk";

export async function getAdminLocale(): Promise<Locale> {
  const value = (await cookies()).get(ADMIN_LOCALE_COOKIE)?.value;
  return isLocale(value) ? value : DEFAULT_ADMIN_LOCALE;
}

/** Server components and actions: `const t = await adminT("listings")`. */
export async function adminT<N extends AdminNamespace>(namespace: N) {
  return getTranslations({ locale: await getAdminLocale(), namespace: `admin.${namespace}` });
}

type AdminNamespace = keyof AdminMessages;
