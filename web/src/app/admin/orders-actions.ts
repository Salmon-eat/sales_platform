"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { adminFetch } from "@/lib/auth";

function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/orders");
  redirect(`/admin/orders${qs.size ? `?${qs}` : ""}`);
}

/** The money arrived some other way (a transfer): switch the extra on. */
export async function markOrderPaid(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  try {
    await adminFetch(`/admin/orders/${id}/paid`, {
      method: "POST",
      body: { note: String(form.get("note") ?? "").trim() || null },
    });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "paid" });
}

export async function cancelOrder(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  try {
    await adminFetch(`/admin/orders/${id}/cancel`, { method: "POST" });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "cancelled" });
}
