"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { MyListing, MyListingDetail } from "@/lib/types";

/** What the form sends; the API checks it again, this is only the shape. */
export type AdInput = {
  category_id: number;
  location_id: number;
  lang: string;
  title: string;
  description: string;
  price: number | null;
  price_period: string | null;
  price_kind: "fixed" | "negotiable" | "free" | "from";
  attributes: Record<string, unknown>;
  contact: { name?: string; phone?: string; email?: string; telegram?: string; whatsapp?: string };
};

export type AdResult = { ok: true; listing: MyListingDetail } | { ok: false; error: string };

/** The API answers with a short word ("duplicate_listing"); the page says it in the person's language. */
function reason(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (Array.isArray(error.detail)) {
      const first = error.detail[0] as { loc?: string[]; msg?: string } | undefined;
      return first?.loc?.[1] ? `field:${first.loc[1]}` : "invalid";
    }
    if (error.status === 401) return "signed_out";
    if (error.status === 429) return "too_many";
  }
  return "generic";
}

async function withToken<T>(run: (token: string) => Promise<T>): Promise<T | { ok: false; error: string }> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  return run(token);
}

export async function saveAd(input: AdInput, lang: string, id?: number): Promise<AdResult> {
  return withToken(async (token) => {
    try {
      const listing = await apiFetch<MyListingDetail>(
        id ? `/my/listings/${id}?lang=${lang}` : `/my/listings?lang=${lang}`,
        { method: id ? "PUT" : "POST", body: input, token },
      );
      revalidatePath("/", "layout");
      return { ok: true as const, listing };
    } catch (error) {
      return { ok: false as const, error: reason(error) };
    }
  }) as Promise<AdResult>;
}

export async function actOnAd(
  id: number,
  action: "submit" | "close" | "reopen" | "extend",
  lang: string,
): Promise<AdResult> {
  return withToken(async (token) => {
    try {
      const listing = await apiFetch<MyListingDetail>(`/my/listings/${id}/actions?lang=${lang}`, {
        method: "POST",
        body: { action },
        token,
      });
      revalidatePath("/", "layout");
      return { ok: true as const, listing };
    } catch (error) {
      return { ok: false as const, error: reason(error) };
    }
  }) as Promise<AdResult>;
}

export async function deleteAd(id: number): Promise<{ ok: boolean; error?: string }> {
  return withToken(async (token) => {
    try {
      await apiFetch(`/my/listings/${id}`, { method: "DELETE", token });
      revalidatePath("/", "layout");
      return { ok: true };
    } catch (error) {
      return { ok: false, error: reason(error) };
    }
  }) as Promise<{ ok: boolean; error?: string }>;
}

export async function deletePhoto(listingId: number, photoId: number): Promise<{ ok: boolean }> {
  return withToken(async (token) => {
    try {
      await apiFetch(`/my/listings/${listingId}/photos/${photoId}`, { method: "DELETE", token });
      return { ok: true };
    } catch {
      return { ok: false };
    }
  }) as Promise<{ ok: boolean }>;
}

export async function myAds(lang: string): Promise<MyListing[]> {
  const token = await accountToken();
  if (!token) return [];
  return apiFetch<MyListing[]>(`/my/listings?lang=${lang}`, { token }).catch(() => []);
}
