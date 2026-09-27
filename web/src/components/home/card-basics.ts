import { useTranslations } from "next-intl";

import type { Locale } from "@/i18n/routing";
import { formatEuro, formatSalaryRange } from "@/lib/listing-format";
import { prefixed } from "@/lib/routes";
import { useViewed } from "@/lib/saved";
import type { ListingCard } from "@/lib/types";

const PERIOD = { month: "perMonth", week: "perWeek", day: "perDay", hour: "perHour" } as const;

/** What every listing card needs, whatever it looks like (the job card, the list row, the photo tile):
 * where it leads, where the ad is, and whether this visitor has opened it already. */
export function useCardBasics(listing: ListingCard, locale: Locale) {
  const t = useTranslations("listing");
  const viewed = useViewed().has(listing.id);
  return {
    href: prefixed(locale, listing.path),
    place: listing.location_scope === "spain_wide" ? t("spainWide") : listing.location?.name,
    viewed,
  };
}

/** What an ad costs, as the cards show it: the price (or a job's salary), "free", "negotiable"; and
 * "/month" when it is paid by the period. */
export function useAdPrice(listing: ListingCard, locale: Locale): { money: string; per: string | null } {
  const t = useTranslations("listing");
  const salary = formatSalaryRange(listing.salary_min, listing.salary_max, locale);
  const price = listing.price !== null && listing.price !== undefined ? formatEuro(listing.price, locale) : null;
  const period = listing.price_period ?? listing.salary_period ?? null;
  const money =
    listing.price_kind === "free"
      ? t("priceFree")
      : (salary ?? price ?? (listing.price_kind === "negotiable" ? t("priceAsk") : t("salaryNone")));
  return { money, per: period && (salary || price) ? t(PERIOD[period]) : null };
}
