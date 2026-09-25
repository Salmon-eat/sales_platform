"use server";

import { revalidatePath } from "next/cache";

import { accountToken } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { Order, ServicePrices } from "@/lib/types";

function reason(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.status === 401) return "signed_out";
  }
  return "generic";
}

/** The price list is the same for everybody, so it is cached like any other public data. */
export async function getPrices(): Promise<ServicePrices> {
  return apiFetch<ServicePrices>("/services", { revalidate: 300 }).catch(() => ({
    products: [],
    card_payments: false,
  }));
}

export async function myOrders(): Promise<Order[]> {
  const token = await accountToken();
  if (!token) return [];
  return apiFetch<Order[]>("/my/orders", { token }).catch(() => []);
}

export type OrderResult =
  | { ok: true; order: Order; checkout?: string }
  | { ok: false; error: string };

/** Order an extra. With the card set up we also get the link to Stripe's page. */
export async function buy(product: string, targetId: number): Promise<OrderResult> {
  const token = await accountToken();
  if (!token) return { ok: false, error: "signed_out" };
  try {
    const order = await apiFetch<Order>("/my/orders", {
      method: "POST",
      body: { product, target_id: targetId },
      token,
    });
    revalidatePath("/", "layout");
    try {
      const { url } = await apiFetch<{ url: string }>(`/my/orders/${order.id}/checkout`, {
        method: "POST",
        token,
      });
      return { ok: true, order, checkout: url };
    } catch {
      // the card is not set up yet: the order waits for the team to confirm a transfer
      return { ok: true, order };
    }
  } catch (error) {
    return { ok: false, error: reason(error) };
  }
}
