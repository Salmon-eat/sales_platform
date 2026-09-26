"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { adminFetch } from "@/lib/auth";

function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/posts");
  revalidatePath("/", "layout");
  redirect(`/admin/posts${qs.size ? `?${qs}` : ""}`);
}

function body(form: FormData) {
  const text = (key: string) => String(form.get(key) ?? "").trim();
  return {
    title: text("title"),
    lang: text("lang") || "es",
    excerpt: text("excerpt"),
    body: text("body"),
    cover: text("cover") || null,
    slug: text("slug") || null,
    status: form.get("status") === "published" ? "published" : "draft",
  };
}

/** New article, or a change to one that exists. */
export async function savePost(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  try {
    if (id) await adminFetch(`/admin/posts/${id}`, { method: "PUT", body: body(form) });
    else await adminFetch("/admin/posts", { method: "POST", body: body(form) });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "saved" });
}

export async function deletePost(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  try {
    await adminFetch(`/admin/posts/${id}`, { method: "DELETE" });
  } catch {
    back({ error: "failed" });
  }
  back({ ok: "deleted" });
}
