"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import { adminFetch } from "@/lib/auth";

/** Results go back as codes in the URL; the page shows them in the admin language. */
function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/links");
  revalidatePath("/admin");
  redirect(`/admin/links${qs.size ? `?${qs}` : ""}`);
}

function errorCodes(error: ApiError): string {
  const detail = error.detail as string | { msg?: string }[] | undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (d.msg ?? "").replace(/^Value error, /, "")).filter(Boolean).join(",") || "failed";
  }
  return "failed";
}

function body(form: FormData) {
  const text = (key: string) => String(form.get(key) ?? "").trim();
  const cost = text("cost").replace(",", ".");
  return {
    name: text("name"),
    code: text("code").toLowerCase() || null, // empty on create: the API makes a short one from the nickname
    channel: text("channel"),
    target_path: text("target_path") || "/",
    cost: cost ? cost : null,
    notes: text("notes") || null,
  };
}

/** The campaign is over: the link goes to the history tab with its numbers. */
export async function closeLink(form: FormData) {
  const id = Number(form.get("id"));
  try {
    await adminFetch(`/admin/links/${id}/close`, { method: "POST" });
  } catch (error) {
    if (error instanceof ApiError) back({ error: errorCodes(error) });
    throw error;
  }
  back({ ok: "closed" });
}

export async function saveLink(form: FormData) {
  const id = Number(form.get("id")) || null;
  let saved: { code: string };
  try {
    saved = await adminFetch<{ code: string }>(id ? `/admin/links/${id}` : "/admin/links", {
      method: id ? "PUT" : "POST",
      body: body(form),
    });
  } catch (error) {
    if (error instanceof ApiError) back({ error: errorCodes(error) });
    throw error;
  }
  back({ ok: id ? "saved" : "created", code: saved.code });
}
