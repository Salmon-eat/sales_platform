"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { adminFetch } from "@/lib/auth";

function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/search-words");
  redirect(`/admin/search-words${qs.size ? `?${qs}` : ""}`);
}

/** Yes or no to a word the site wants to learn. "Yes" may point at a different category than guessed. */
export async function decideWord(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  const category = String(form.get("category_id") ?? "").trim();
  try {
    await adminFetch(`/admin/search-words/proposals/${id}`, {
      method: "POST",
      body: {
        action: String(form.get("action") ?? "ignore"),
        category_id: category ? Number(category) : null,
      },
    });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "1" });
}

/** Run the nightly collection now, so somebody can watch it work instead of waiting until 03:20. */
export async function collectWords(): Promise<void> {
  try {
    await adminFetch("/admin/search-words/collect", { method: "POST", body: {} });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "1" });
}
