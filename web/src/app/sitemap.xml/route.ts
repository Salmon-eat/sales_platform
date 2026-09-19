import { LOCALES, localePrefix } from "@/i18n/routing";
import { getSitemapIndex } from "@/lib/api";
import { sitemapIndex, xmlResponse } from "@/lib/sitemap-xml";

export const revalidate = 3600;

/** Sitemap index: per language static pages, list pages and cards, 40k URLs per file (spec §6). */
export async function GET() {
  const counts = await getSitemapIndex().catch(() => null);
  const files = LOCALES.flatMap((locale) => {
    const code = localePrefix(locale).slice(1);
    const pages = counts?.[locale] ?? { lists: 1, listings: 1 };
    return [
      `${code}-static.xml`,
      ...Array.from({ length: pages.lists }, (_, i) => `${code}-lists-${i + 1}.xml`),
      ...Array.from({ length: pages.listings }, (_, i) => `${code}-listings-${i + 1}.xml`),
    ];
  });
  return xmlResponse(sitemapIndex(files));
}
