import "server-only";

import { cookies } from "next/headers";

import { ApiError, apiFetch } from "./api";
import { ACCOUNT_COOKIE } from "./account-constants";
import type { Account } from "./types";

export async function accountToken(): Promise<string | undefined> {
  return (await cookies()).get(ACCOUNT_COOKIE)?.value;
}

/** The signed-in visitor, or null for a guest. Never throws on an expired session. */
export async function getAccount(): Promise<Account | null> {
  const token = await accountToken();
  if (!token) return null;
  try {
    return await apiFetch<Account>("/account/me", { token });
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
    throw error;
  }
}

/** A call on behalf of the visitor; returns null when the session is gone. */
export async function accountFetch<T>(
  path: string,
  options: Omit<NonNullable<Parameters<typeof apiFetch>[1]>, "token"> = {},
): Promise<T | null> {
  const token = await accountToken();
  if (!token) return null;
  try {
    return await apiFetch<T>(path, { ...options, token });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}
