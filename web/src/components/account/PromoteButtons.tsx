"use client";

import { ArrowUp, Sparkles, Star } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { buy } from "@/app/[locale]/order-actions";
import { asLocale } from "@/i18n/routing";
import type { Product } from "@/lib/types";

const ICONS = { bump: ArrowUp, highlight_7: Sparkles, top_7: Star } as const;

/** "Raise it", "colour it", "put it on top": ordering an extra for one of my ads. */
export function PromoteButtons({ listingId, products }: { listingId: number; products: Product[] }) {
  const t = useTranslations("promote");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" });

  async function order(product: string) {
    setBusy(true);
    setError(null);
    const result = await buy(product, listingId);
    setBusy(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    if (result.checkout) {
      window.location.href = result.checkout;
      return;
    }
    // no card account yet: the order waits for the team to confirm the transfer
    setDone(product);
    router.refresh();
  }

  if (done) return <p className="promote__done muted small">{t("ordered")}</p>;

  return (
    <div className="promote">
      {products
        .filter((product) => product.target === "listing")
        .map((product) => {
          const Icon = ICONS[product.key as keyof typeof ICONS] ?? Star;
          return (
            <button
              key={product.key}
              type="button"
              className="btn btn--outline btn--sm"
              disabled={busy}
              onClick={() => order(product.key)}
              title={t(`${product.key}_hint` as "bump_hint")}
            >
              <Icon size={14} aria-hidden /> {t(product.key as "bump")} · {money.format(product.amount / 100)}
            </button>
          );
        })}
      {error && (
        <span className="form-error">
          {t.has(`errors.${error}` as "errors.generic")
            ? t(`errors.${error}` as "errors.generic")
            : t("errors.generic")}
        </span>
      )}
    </div>
  );
}
