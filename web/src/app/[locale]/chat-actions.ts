"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { Chat, ChatDetail } from "@/lib/types";

export type ChatResult = { ok: true; chat: ChatDetail } | { ok: false; error: string };

function reason(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.status === 401) return "signed_out";
    if (error.status === 429) return "too_many";
  }
  return "generic";
}

/** The buyer's first message about an ad; writing again continues the same conversation. */
export async function writeToSeller(listingId: number, text: string, lang: string): Promise<ChatResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const chat = await apiFetch<ChatDetail>(`/my/chats?lang=${lang}`, {
      method: "POST",
      body: { listing_id: listingId, text },
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true, chat };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

export async function replyInChat(chatId: number, text: string, lang: string): Promise<ChatResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const chat = await apiFetch<ChatDetail>(`/my/chats/${chatId}/messages?lang=${lang}`, {
      method: "POST",
      body: { text },
      token,
    });
    revalidatePath("/", "layout");
    return { ok: true, chat };
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}

/** Opening a conversation marks what the other side wrote as read. */
export async function openChat(chatId: number, lang: string): Promise<ChatDetail | null> {
  const token = await accountToken();
  if (!token) return null;
  try {
    const chat = await apiFetch<ChatDetail>(`/my/chats/${chatId}?lang=${lang}`, { token });
    revalidatePath("/", "layout");
    return chat;
  } catch {
    return null;
  }
}

export async function myChats(lang: string): Promise<Chat[]> {
  const token = await accountToken();
  if (!token) return [];
  return apiFetch<Chat[]>(`/my/chats?lang=${lang}`, { token }).catch(() => []);
}

export async function hideChat(chatId: number): Promise<void> {
  const token = await accountToken();
  if (!token) return;
  await apiFetch(`/my/chats/${chatId}/hide`, { method: "POST", token }).catch(() => undefined);
  revalidatePath("/", "layout");
}
