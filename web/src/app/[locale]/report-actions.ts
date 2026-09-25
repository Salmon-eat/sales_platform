"use server";

import { headers } from "next/headers";

import { accountToken } from "@/lib/account";
import { apiFetch } from "@/lib/api";

export type ReportReason =
  | "fraud"
  | "prohibited"
  | "spam"
  | "wrong_category"
  | "duplicate"
  | "offensive"
  | "sold"
  | "other";

/** Anyone reading the site can report an ad; signing in is not required. */
export async function reportListing(
  listingId: number,
  reason: ReportReason,
  note: string,
): Promise<{ ok: boolean }> {
  const token = await accountToken();
  // the visitor's own address, so the per-address limit applies to them and not to our server
  const forwarded = (await headers()).get("x-forwarded-for") ?? undefined;
  try {
    await apiFetch("/reports", {
      method: "POST",
      body: { listing_id: listingId, reason, note: note.trim() || null },
      token,
      clientIp: forwarded?.split(",")[0]?.trim(),
    });
    return { ok: true };
  } catch {
    return { ok: false };
  }
}
