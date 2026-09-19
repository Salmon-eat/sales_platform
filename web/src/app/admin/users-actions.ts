"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import { adminFetch } from "@/lib/auth";

/** Results go back as codes in the URL; the page shows them in the admin language. */
function back(params?: Record<string, string>): never {
  const qs = new URLSearchParams(params);
  revalidatePath("/admin/users");
  redirect(`/admin/users${qs.size ? `?${qs}` : ""}`);
}

async function call(path: string, init: Parameters<typeof adminFetch>[1]) {
  try {
    await adminFetch(path, init);
  } catch (error) {
    if (error instanceof ApiError) {
      const code = typeof error.detail === "string" ? error.detail : error.status === 422 ? "email" : "failed";
      back({ error: code });
    }
    throw error;
  }
}

export async function addUser(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const name = String(formData.get("name") ?? "").trim() || null;
  const role = formData.get("role") === "admin" ? "admin" : "manager";
  await call("/admin/users", { method: "POST", body: { email, name, role } });
  back({ ok: "added", email });
}

export async function updateUser(formData: FormData) {
  const id = Number(formData.get("id"));
  const body: Record<string, unknown> = {};
  const role = formData.get("role");
  if (role === "admin" || role === "manager") body.role = role;
  const active = formData.get("is_active");
  if (active === "true" || active === "false") body.is_active = active === "true";
  await call(`/admin/users/${id}`, { method: "PATCH", body });
  back();
}

export async function signOutUser(formData: FormData) {
  const id = Number(formData.get("id"));
  await call(`/admin/users/${id}/logout-all`, { method: "POST" });
  back({ ok: "closed" });
}
