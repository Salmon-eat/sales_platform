"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { translateApiErrors } from "@/lib/admin-errors";
import { ApiError } from "@/lib/api";
import { adminFetch } from "@/lib/auth";
import type { AdminListingDetail, ListingAction } from "@/lib/types";

export type SaveResult = { ok: true; id: number } | { ok: false; errors: string[] };

type ErrorDetail = Parameters<typeof translateApiErrors>[0];

async function call<T>(path: string, init: Parameters<typeof adminFetch>[1]): Promise<{ data?: T; errors?: string[] }> {
  try {
    return { data: await adminFetch<T>(path, init) };
  } catch (error) {
    if (error instanceof ApiError && error.detail !== undefined) {
      return { errors: await translateApiErrors(error.detail as ErrorDetail) };
    }
    throw error;
  }
}

function refresh(id?: number) {
  revalidatePath("/admin/listings");
  if (id) revalidatePath(`/admin/listings/${id}`);
  revalidatePath("/[locale]", "layout"); // public pages show listings
}

const withError = (target: string, error: string) =>
  `${target}${target.includes("?") ? "&" : "?"}error=${encodeURIComponent(error)}`;

export async function saveListing(id: number | null, payload: unknown, publish: boolean): Promise<SaveResult> {
  const saved = await call<AdminListingDetail>(id ? `/admin/listings/${id}` : "/admin/listings", {
    method: id ? "PUT" : "POST",
    body: payload,
  });
  if (!saved.data) return { ok: false, errors: saved.errors ?? (await translateApiErrors(undefined)) };

  if (publish && ["draft", "pending", "rejected"].includes(saved.data.status)) {
    const published = await call(`/admin/listings/${saved.data.id}/actions`, {
      method: "POST",
      body: { action: "publish" },
    });
    if (published.errors) return { ok: false, errors: published.errors };
  }
  refresh(saved.data.id);
  return { ok: true, id: saved.data.id };
}

export async function runListingAction(formData: FormData) {
  const id = Number(formData.get("id"));
  const action = String(formData.get("action")) as ListingAction | "delete";
  const back = String(formData.get("back") ?? "");
  const target = back || `/admin/listings/${id}`;

  if (action === "delete") {
    const deleted = await call(`/admin/listings/${id}`, { method: "DELETE" });
    if (deleted.errors) redirect(withError(target, deleted.errors[0]));
    refresh();
    redirect("/admin/listings");
  }

  const result = await call(`/admin/listings/${id}/actions`, {
    method: "POST",
    body: { action, days: Number(formData.get("days") ?? 30) },
  });
  refresh(id);
  if (result.errors) redirect(withError(target, result.errors[0]));
  redirect(target);
}
