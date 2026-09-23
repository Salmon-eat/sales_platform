import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";

import { HomeShowcase } from "@/components/home/HomeShowcase";
import { asLocale } from "@/i18n/routing";
import { getHome, orFallback } from "@/lib/api";
import { routeAlternates } from "@/lib/seo";

export const revalidate = 60;

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  return { alternates: routeAlternates(locale, { type: "home" }) };
}

const EMPTY = { totals: { listings: 0, today: 0, sections: 0 }, sections: [], promoted: [], fresh: [] };

/** Home: the whole board at a glance — search, sections, paid placements, the newest ads. */
export default async function HomePage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const home = await orFallback(getHome(locale), EMPTY);

  return <HomeShowcase locale={locale} home={home} />;
}
