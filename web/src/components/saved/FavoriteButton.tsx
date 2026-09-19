"use client";

import { Heart } from "lucide-react";
import { useTranslations } from "next-intl";

import { useFavorites } from "@/lib/saved";

/** Heart toggle. `label` shows text next to the icon (card page); list cards use the icon only. */
export function FavoriteButton({ id, withLabel = false }: { id: number; withLabel?: boolean }) {
  const t = useTranslations();
  const { has, toggle } = useFavorites();
  const saved = has(id);
  const label = saved ? t("listing.saved") : t("listing.addFavorite");

  return (
    <button
      type="button"
      className={`favorite ${saved ? "favorite--on" : ""} ${withLabel ? "favorite--label" : ""}`}
      aria-pressed={saved}
      aria-label={withLabel ? undefined : label}
      title={label}
      onClick={() => toggle(id)}
    >
      <Heart size={19} fill={saved ? "currentColor" : "none"} aria-hidden />
      {withLabel && <span>{saved ? t("listingPage.savedLabel") : t("listingPage.save")}</span>}
    </button>
  );
}
