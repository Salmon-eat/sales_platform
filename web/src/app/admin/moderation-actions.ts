"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import { adminFetch } from "@/lib/auth";

function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/moderation");
  revalidatePath("/admin");
  redirect(`/admin/moderation${qs.size ? `?${qs}` : ""}`);
}

function code(error: unknown): string {
  return error instanceof ApiError && typeof error.detail === "string" ? error.detail : "failed";
}

/** The ad is fine: it goes live for the usual thirty days. */
export async function approveAd(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  try {
    await adminFetch(`/admin/moderation/${id}/approve`, { method: "POST" });
  } catch (error) {
    back({ error: code(error) });
  }
  back({ ok: "approved" });
}

/** Refused with a reason the author will read in their own area. */
export async function rejectAd(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  const body = {
    reason: String(form.get("reason") ?? "other"),
    note: String(form.get("note") ?? "").trim() || null,
  };
  try {
    await adminFetch(`/admin/moderation/${id}/reject`, { method: "POST", body });
  } catch (error) {
    back({ error: code(error) });
  }
  back({ ok: "rejected" });
}
