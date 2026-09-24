"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { Resume, ResumeInput } from "@/lib/types";

export type ResumeResult = { ok: true; resume: Resume } | { ok: false; error: string };

function reason(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (Array.isArray(error.detail)) return "invalid";
    if (error.status === 401) return "signed_out";
  }
  return "generic";
}

export async function getResume(lang: string): Promise<Resume | null> {
  const token = await accountToken();
  if (!token) return null;
  return apiFetch<Resume | null>(`/my/resume?lang=${lang}`, { token }).catch(() => null);
}

export async function saveResume(input: ResumeInput, lang: string): Promise<ResumeResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const resume = await apiFetch<Resume>(`/my/resume?lang=${lang}`, {
      method: "PUT",
      body: input,
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true, resume };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function deleteResumeFile(lang: string): Promise<ResumeResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    await apiFetch(`/my/resume/file`, { method: "DELETE", token });
    const resume = await apiFetch<Resume>(`/my/resume?lang=${lang}`, { token });
    revalidatePath("/", "layout");
    return { ok: true, resume };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function deleteResume(): Promise<{ ok: boolean }> {
  const token = await accountToken();
  if (!token) return { ok: false };
  await apiFetch(`/my/resume`, { method: "DELETE", token }).catch(() => undefined);
  revalidatePath("/", "layout");
  return { ok: true };
}

export type ApplyResult =
  | { ok: true; duplicate: boolean; withFile: boolean }
  | { ok: false; error: string };

/** One press on a vacancy: the application goes to the managers with the CV attached. */
export async function applyWithResume(
  listingId: number,
  comment?: string,
  questions: Record<string, string> = {},
): Promise<ApplyResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const answer = await apiFetch<{ duplicate: boolean; with_file: boolean }>("/my/apply", {
      method: "POST",
      body: { listing_id: listingId, comment: comment || null, questions },
      token,
    });
    return { ok: true, duplicate: answer.duplicate, withFile: answer.with_file };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}
