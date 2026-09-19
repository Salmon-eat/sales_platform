"use server";

import { revalidatePath } from "next/cache";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import { adminT } from "@/lib/admin-locale";
import { ApiError, apiFetch } from "@/lib/api";
import { adminFetch, getToken } from "@/lib/auth";
import { AUTH_COOKIE, AUTH_COOKIE_MAX_AGE } from "@/lib/auth-constants";

export type LoginState = { error?: string };

type SessionOut = { token: string; expires_at: string };

const LOGIN_ERRORS = { 401: "error_401", 403: "error_403", 429: "error_429", 503: "error_503" } as const;

/** The visitor's address as Caddy wrote it (Caddy overwrites whatever the browser sent). */
async function visitorIp(): Promise<string | undefined> {
  const forwarded = (await headers()).get("x-forwarded-for");
  const ip = forwarded?.split(",")[0]?.trim();
  return ip && /^[0-9a-fA-F:.]{3,45}$/.test(ip) ? ip : undefined;
}

async function startSession(path: string, body: unknown): Promise<LoginState> {
  const t = await adminT("login");
  let session: SessionOut;
  try {
    // sign-in attempts are limited per visitor IP, not per our server
    session = await apiFetch<SessionOut>(path, { method: "POST", body, clientIp: await visitorIp() });
  } catch (error) {
    if (error instanceof ApiError && error.status in LOGIN_ERRORS) {
      return { error: t(LOGIN_ERRORS[error.status as keyof typeof LOGIN_ERRORS]) };
    }
    console.error(error);
    return { error: t("error_other") };
  }
  (await cookies()).set(AUTH_COOKIE, session.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: AUTH_COOKIE_MAX_AGE,
  });
  redirect("/admin");
}

/** Credential (ID token) from the Google button -> API checks it and the email whitelist. */
export async function googleLogin(credential: string): Promise<LoginState> {
  if (typeof credential !== "string" || credential.length < 20) return { error: (await adminT("login"))("error_401") };
  return startSession("/auth/google", { credential });
}

/** Local development without a Google client (ADMIN_DEV_LOGIN, refused by the API in production). */
export async function devLogin(_: LoginState, formData: FormData): Promise<LoginState> {
  return startSession("/auth/dev-login", { email: String(formData.get("email") ?? "") });
}

const APPLICATION_STATUSES = ["new", "in_progress", "done", "rejected"];

export async function setApplicationStatus(formData: FormData) {
  const id = Number(formData.get("id"));
  const status = String(formData.get("status"));
  if (!Number.isInteger(id) || !APPLICATION_STATUSES.includes(status)) return;
  await adminFetch(`/admin/applications/${id}`, { method: "PATCH", body: { status } });
  revalidatePath("/admin/applications", "layout");
}

/** A manager's reply in the site chat: the visitor sees it in the orange window. */
export async function replyInChat(formData: FormData) {
  const id = Number(formData.get("id"));
  const text = String(formData.get("text") ?? "").trim();
  if (!Number.isInteger(id) || !text) return;
  await adminFetch(`/admin/applications/${id}/messages`, { method: "POST", body: { text } });
  revalidatePath("/admin/applications", "layout");
}

/** GDPR erasure on request (admins only): contacts disappear from all the person's applications. */
export async function erasePerson(formData: FormData) {
  const id = Number(formData.get("id"));
  if (!Number.isInteger(id)) return;
  const result = await adminFetch<{ erased: number }>(`/admin/applications/${id}/erase`, { method: "POST" });
  revalidatePath("/admin/applications", "layout");
  redirect(`/admin/applications/${id}?erased=${result.erased}`);
}

async function endSession(path: "/auth/logout" | "/auth/logout-all") {
  const token = await getToken();
  if (token) {
    // a session that is already gone is fine here
    await apiFetch(path, { method: "POST", token }).catch(() => undefined);
  }
  (await cookies()).delete(AUTH_COOKIE);
  redirect("/admin/login");
}

export async function logout() {
  await endSession("/auth/logout");
}

/** admin spec §1: "Вийти на всіх пристроях" after a lost phone. */
export async function logoutEverywhere() {
  await endSession("/auth/logout-all");
}
