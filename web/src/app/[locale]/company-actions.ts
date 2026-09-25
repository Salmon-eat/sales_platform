"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { MyCompany } from "@/lib/types";

export type CompanyInput = {
  name: string;
  lang: string;
  about: string;
  city_id: number | null;
  address: string | null;
  hours: string | null;
  category_ids: number[];
  phone: string | null;
  whatsapp: string | null;
  telegram: string | null;
  email: string | null;
  site: string | null;
};

export type CompanyResult = { ok: true; company: MyCompany } | { ok: false; error: string };

function reason(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (Array.isArray(error.detail)) {
      const first = error.detail[0] as { loc?: string[] } | undefined;
      return first?.loc?.[1] ? `field:${first.loc[1]}` : "invalid";
    }
    if (error.status === 401) return "signed_out";
  }
  return "generic";
}

export async function getMyCompany(lang: string): Promise<MyCompany | null> {
  const token = await accountToken();
  if (!token) return null;
  return apiFetch<MyCompany | null>(`/my/company?lang=${lang}`, { token }).catch(() => null);
}

export async function saveCompany(input: CompanyInput, lang: string): Promise<CompanyResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const company = await apiFetch<MyCompany>(`/my/company?lang=${lang}`, {
      method: "PUT",
      body: input,
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true, company };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function actOnCompany(
  action: "submit" | "hide" | "reopen",
  lang: string,
): Promise<CompanyResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const company = await apiFetch<MyCompany>(`/my/company/actions?lang=${lang}`, {
      method: "POST",
      body: { action },
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true, company };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function deleteCompany(): Promise<{ ok: boolean }> {
  const token = await accountToken();
  if (!token) return { ok: false };
  await apiFetch("/my/company", { method: "DELETE", token }).catch(() => undefined);
  revalidatePath("/", "layout");
  return { ok: true };
}
