import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getAdminLocale } from "./admin-locale";
import { ApiError, apiFetch } from "./api";
import { AUTH_COOKIE } from "./auth-constants";
import type { User } from "./types";

export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(AUTH_COOKIE)?.value;
}

export async function getCurrentUser(): Promise<User | null> {
  const token = await getToken();
  if (!token) return null;
  try {
    return await apiFetch<User>("/auth/me", { token });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** Admin-only screens (dictionaries, content, SEO, users): managers go back to the dashboard.
 * The API checks the role again on every endpoint; this only avoids showing a broken page. */
export async function requireAdminPage(): Promise<User> {
  const user = await getCurrentUser();
  if (user?.role !== "admin") redirect("/admin");
  return user;
}

/** Authenticated call to /v1/admin/*; sends the user to the login page when the session is gone. */
export async function adminFetch<T>(
  path: string,
  options: Omit<NonNullable<Parameters<typeof apiFetch>[1]>, "token" | "lang"> = {},
): Promise<T> {
  const token = await getToken();
  if (!token) redirect("/admin/login");

  try {
    return await apiFetch<T>(path, { ...options, token, lang: await getAdminLocale() });
  } catch (error) {
    // 401 = the session is gone; 403 = logged in but not allowed (e.g. someone else's listing)
    if (error instanceof ApiError && error.status === 401) {
      redirect("/admin/login");
    }
    throw error;
  }
}
