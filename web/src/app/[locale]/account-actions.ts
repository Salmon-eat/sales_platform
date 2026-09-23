"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { ApiError, apiFetch } from "@/lib/api";
import { ACCOUNT_COOKIE, ACCOUNT_COOKIE_MAX_AGE } from "@/lib/account-constants";
import { accountToken } from "@/lib/account";
import type { Account } from "@/lib/types";

export type SignInState = { ok?: boolean; error?: string };

type SessionOut = { token: string; expires_at: string; user: Account };

/** API answers with a short word ("wrong_code"); the page turns it into a sentence in the visitor's language. */
function reason(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = typeof error.detail === "string" ? error.detail : "";
    if (detail) return detail;
    if (error.status === 429) return "too_many";
    if (error.status === 503) return "unavailable";
  }
  return "generic";
}

async function keepSession(session: SessionOut, ids: number[]): Promise<void> {
  (await cookies()).set(ACCOUNT_COOKIE, session.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: ACCOUNT_COOKIE_MAX_AGE,
  });
  // what the browser kept for a guest moves into the account
  if (ids.length) {
    await apiFetch("/account/favorites", {
      method: "PUT",
      body: { ids: ids.slice(0, 200) },
      token: session.token,
    }).catch(() => undefined);
  }
}

/** Step one: a code to the address. */
export async function requestCode(email: string, lang: string): Promise<SignInState> {
  try {
    await apiFetch("/account/code", { method: "POST", body: { email, lang } });
    return { ok: true };
  } catch (error) {
    return { error: reason(error) };
  }
}

/** Step two: the code from the letter opens the account (and creates it on the first sign-in). */
export async function signInWithCode(
  email: string,
  code: string,
  lang: string,
  favorites: number[] = [],
): Promise<SignInState> {
  try {
    const session = await apiFetch<SessionOut>("/account/session", {
      method: "POST",
      body: { email, code, lang },
    });
    await keepSession(session, favorites);
    return { ok: true };
  } catch (error) {
    return { error: reason(error) };
  }
}

export async function signInWithGoogle(
  credential: string,
  lang: string,
  favorites: number[] = [],
): Promise<SignInState> {
  try {
    const session = await apiFetch<SessionOut>("/account/google", {
      method: "POST",
      body: { credential, lang },
    });
    await keepSession(session, favorites);
    return { ok: true };
  } catch (error) {
    return { error: reason(error) };
  }
}

/** Telegram's widget hands over the person's data signed by the login bot; the API checks the signature. */
export async function signInWithTelegram(
  data: Record<string, string | number>,
  lang: string,
  favorites: number[] = [],
): Promise<SignInState> {
  try {
    const session = await apiFetch<SessionOut>("/account/telegram", {
      method: "POST",
      body: { ...data, lang },
    });
    await keepSession(session, favorites);
    return { ok: true };
  } catch (error) {
    return { error: reason(error) };
  }
}

export async function signOut(): Promise<void> {
  const token = await accountToken();
  if (token) await apiFetch("/account/logout", { method: "POST", token }).catch(() => undefined);
  (await cookies()).delete(ACCOUNT_COOKIE);
  revalidatePath("/", "layout");
}

/** Used straight as a <form action>: it answers with nothing and the page re-renders with the new data. */
export async function updateProfile(formData: FormData): Promise<void> {
  const token = await accountToken();
  if (!token) return;
  const body = {
    name: String(formData.get("name") ?? "").trim(),
    phone: String(formData.get("phone") ?? "").trim() || null,
  };
  await apiFetch("/account/me", { method: "PATCH", body, token }).catch(() => undefined);
  revalidatePath("/", "layout");
}

/** GDPR: the visitor deletes the account themselves, no letters to anyone. */
export async function deleteAccount(): Promise<void> {
  const token = await accountToken();
  if (token) await apiFetch("/account/me", { method: "DELETE", token }).catch(() => undefined);
  (await cookies()).delete(ACCOUNT_COOKIE);
  revalidatePath("/", "layout");
}
