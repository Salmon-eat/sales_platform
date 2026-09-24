"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { apiFetch } from "@/lib/api";
import type { Candidate } from "@/lib/types";

/** Everyone who answered the vacancies this person posted. */
export async function myCandidates(lang: string): Promise<Candidate[]> {
  const token = await accountToken();
  if (!token) return [];
  return apiFetch<Candidate[]>(`/my/candidates?lang=${lang}`, { token }).catch(() => []);
}

export async function setCandidateStatus(
  applicationId: number,
  status: Candidate["status"],
  lang: string,
): Promise<Candidate | null> {
  const token = await accountToken();
  if (!token) return null;
  try {
    const candidate = await apiFetch<Candidate>(`/my/candidates/${applicationId}/status?lang=${lang}`, {
      method: "POST",
      body: { status },
      token,
    });
    revalidatePath("/", "layout");
    return candidate;
  } catch {
    return null;
  }
}

export async function addCandidateNote(
  applicationId: number,
  text: string,
  lang: string,
): Promise<Candidate | null> {
  const token = await accountToken();
  if (!token) return null;
  try {
    return await apiFetch<Candidate>(`/my/candidates/${applicationId}/notes?lang=${lang}`, {
      method: "POST",
      body: { text },
      token,
    });
  } catch {
    return null;
  }
}
