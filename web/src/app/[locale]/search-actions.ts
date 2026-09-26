"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { SavedSearch } from "@/lib/types";

function reason(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.status === 401) return "signed_out";
  }
  return "generic";
}

export type SaveSearchResult = { ok: true; search: SavedSearch } | { ok: false; error: string };

/** Keep this search and hear about what turns up after today. */
export async function saveSearch(
  input: {
    title: string;
    section_key?: string | null;
    category_slug?: string | null;
    location_slug?: string | null;
    params?: Record<string, string>;
  },
  lang: string,
): Promise<SaveSearchResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const search = await apiFetch<SavedSearch>(`/my/searches?lang=${lang}`, {
      method: "POST",
      body: {
        title: input.title,
        section_key: input.section_key ?? null,
        category_slug: input.category_slug ?? null,
        location_slug: input.location_slug ?? null,
        params: input.params ?? {},
      },
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true, search };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function mySearches(): Promise<SavedSearch[]> {
  const token = await accountToken();
  if (!token) return [];
  return apiFetch<SavedSearch[]>("/my/searches", { token }).catch(() => []);
}

export async function setSearchNotify(id: number, notify: boolean): Promise<void> {
  const token = await accountToken();
  if (!token) return;
  await apiFetch(`/my/searches/${id}/notify`, { method: "POST", body: { notify }, token }).catch(
    () => undefined,
  );
  revalidatePath("/", "layout");
}

export async function deleteSearch(id: number): Promise<void> {
  const token = await accountToken();
  if (!token) return;
  await apiFetch(`/my/searches/${id}`, { method: "DELETE", token }).catch(() => undefined);
  revalidatePath("/", "layout");
}
