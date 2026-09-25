"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { adminFetch } from "@/lib/auth";

function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/moderation");
  redirect(`/admin/moderation${qs.size ? `?${qs}` : ""}`);
}

/** The firm's page is fine; "verified" means somebody has actually seen its papers. */
export async function approveCompany(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  const verified = form.get("verified") !== null;
  try {
    await adminFetch(`/admin/companies/${id}/approve?verified=${verified}`, { method: "POST" });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "company" });
}

export async function rejectCompany(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  try {
    await adminFetch(`/admin/companies/${id}/reject`, {
      method: "POST",
      body: {
        reason: String(form.get("reason") ?? "other"),
        note: String(form.get("note") ?? "").trim() || null,
      },
    });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "company" });
}
