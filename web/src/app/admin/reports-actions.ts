"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { adminFetch } from "@/lib/auth";

function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/reports");
  revalidatePath("/admin");
  redirect(`/admin/reports${qs.size ? `?${qs}` : ""}`);
}

/** The complaint is right: the ad goes down, and with a reason given, its author too. */
export async function resolveReport(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  const blockReason = String(form.get("block_reason") ?? "").trim();
  try {
    await adminFetch(`/admin/reports/${id}/resolve`, {
      method: "POST",
      body: {
        action: String(form.get("action") ?? "reject"),
        block_reason: blockReason || null,
      },
    });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "1" });
}
