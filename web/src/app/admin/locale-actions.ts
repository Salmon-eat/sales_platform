"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { isLocale } from "@/i18n/routing";
import { ADMIN_LOCALE_COOKIE } from "@/lib/admin-locale";

export async function setAdminLocale(locale: string) {
  if (!isLocale(locale)) return;
  (await cookies()).set(ADMIN_LOCALE_COOKIE, locale, {
    path: "/admin",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 365,
  });
  revalidatePath("/admin", "layout");
}
