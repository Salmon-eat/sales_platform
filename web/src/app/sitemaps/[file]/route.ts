import { type Locale, LOCALES, localeFromPrefix } from "@/i18n/routing";
import { ApiError, getSitemapPage, getTaxonomy } from "@/lib/api";
import { AGENCY_PAGES, type AppRoute, isIndexable, localizedPath, prefixed, STATIC_PAGES } from "@/lib/routes";
import { prefixAlternates, type SitemapUrl, urlset, xmlResponse } from "@/lib/sitemap-xml";

export const revalidate = 3600;

const FILE_RE = /^(es|en|ua|ru)-(static|lists|listings)(?:-(\d+))?\.xml$/;

/** Agency services: catalog, sectors and service pages (always indexed, spec §6). */
async function serviceUrls(locale: Locale): Promise<SitemapUrl[]> {
  const taxonomy = await getTaxonomy(locale).catch(() => null);
  const urls: SitemapUrl[] = [];
  for (const section of taxonomy?.sections.filter((s) => s.kind === "services" && s.is_enabled) ?? []) {
    const entry = (slugs?: Record<Locale, string>) => {
      const alternates = Object.fromEntries(
        LOCALES.map((l) => [l, prefixed(l, [section.slugs[l], slugs?.[l]].filter(Boolean).join("/"))]),
      ) as Record<Locale, string>;
      return { path: alternates[locale], alternates };
    };
    urls.push(entry());
    for (const sector of section.categories) {
      urls.push(entry(sector.slugs));
      for (const service of sector.children) urls.push(entry(service.slugs));
    }
  }
  return urls;
}

/** /sitemaps/ua-static.xml, /sitemaps/es-lists-1.xml, /sitemaps/en-listings-2.xml */
export async function GET(_request: Request, { params }: { params: Promise<{ file: string }> }) {
  const match = FILE_RE.exec((await params).file);
  const locale = localeFromPrefix(match?.[1]);
  if (!match || !locale || (match[2] !== "static" && !match[3])) return new Response("Not found", { status: 404 });

  if (match[2] === "static") {
    const routes = [
      { type: "home" } as AppRoute,
      ...AGENCY_PAGES.map((p): AppRoute => ({ type: "agency", key: p.key })),
      ...STATIC_PAGES.map((p): AppRoute => ({ type: "static", key: p.key })),
    ].filter(isIndexable);
    const urls: SitemapUrl[] = routes.map((route) => ({
      path: localizedPath(locale, route),
      alternates: Object.fromEntries(LOCALES.map((l) => [l, localizedPath(l, route)])),
    }));
    return xmlResponse(urlset([...urls, ...(await serviceUrls(locale))]));
  }

  try {
    const data = await getSitemapPage(locale, match[2] as "lists" | "listings", Number(match[3]));
    const urls = data.items.map((item) => {
      const alternates = prefixAlternates(item.alternates);
      return { path: alternates[locale] ?? item.path, lastmod: item.lastmod, alternates };
    });
    return xmlResponse(urlset(urls));
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) return new Response("Not found", { status: 404 });
    throw error;
  }
}
