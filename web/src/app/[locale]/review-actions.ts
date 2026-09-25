"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";

export type ReviewResult = { ok: true } | { ok: false; error: string };

function reason(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === "string") return error.detail;
  if (error instanceof ApiError && error.status === 401) return "signed_out";
  return "generic";
}

/** A review of a seller; the API refuses one from somebody who never wrote to them. */
export async function leaveReview(
  sellerId: number,
  rating: number,
  text: string,
): Promise<ReviewResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    await apiFetch("/my/reviews", {
      method: "POST",
      body: { seller_id: sellerId, rating, text: text.trim() },
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

/** The seller's answer to a review about them. */
export async function replyToReview(reviewId: number, text: string): Promise<ReviewResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    await apiFetch(`/my/reviews/${reviewId}/reply`, { method: "POST", body: { text: text.trim() }, token });
    revalidatePath("/", "layout");
    return { ok: true };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function myReviews(): Promise<{ about_me: Review[]; written: Review[] }> {
  const token = await accountToken();
  if (!token) return { about_me: [], written: [] };
  return apiFetch<{ about_me: Review[]; written: Review[] }>("/my/reviews", { token }).catch(() => ({
    about_me: [],
    written: [],
  }));
}

export type Review = {
  id: number;
  rating: number;
  text: string;
  reply: string | null;
  replied_at: string | null;
  author_name: string;
  seller_name: string;
  listing_id: number | null;
  created_at: string;
};
