import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";

import { ApplicationSection } from "@/components/apply/ApplicationSection";
import { DriversBanner } from "@/components/home/DriversBanner";
import { Hero } from "@/components/home/Hero";
import { HomeCatalog } from "@/components/search/ListPage";
import { asLocale } from "@/i18n/routing";
import { getListingStats, orFallback } from "@/lib/api";
import { getApplicationOptions } from "@/lib/application-options";
import { routeAlternates } from "@/lib/seo";

export const revalidate = 60;

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  return { alternates: routeAlternates(locale, { type: "home" }) };
}

/** Home: hero with search, then straight into the jobs catalog with filters (design mockup), then promo blocks. */
export default async function HomePage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);

  const [{ sectors, cities, taxonomy }, stats] = await Promise.all([
    getApplicationOptions(locale),
    orFallback(getListingStats(), { total: 0, today: 0 }),
  ]);

  return (
    <>
      <Hero locale={locale} stats={stats} taxonomy={taxonomy} />
      <HomeCatalog locale={locale} />
      <div className="container home-content">
        <DriversBanner locale={locale} />
        <ApplicationSection options={{ sectors, cities }} />
      </div>
    </>
  );
}
