import { LOCALES, type Locale, X_DEFAULT_LOCALE } from "@/i18n/routing";

import { prefixed } from "./routes";
import { absoluteUrl } from "./seo";

export type SitemapUrl = { path: string; lastmod?: string | null; alternates?: Partial<Record<Locale, string>> };

const escape = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Paths here already include the language prefix. */
export function urlset(urls: SitemapUrl[]): string {
  const body = urls
    .map((u) => {
      const links = LOCALES.filter((l) => u.alternates?.[l])
        .map((l) => `<xhtml:link rel="alternate" hreflang="${l}" href="${escape(absoluteUrl(u.alternates![l]!))}"/>`)
        .concat(
          u.alternates?.[X_DEFAULT_LOCALE]
            ? [`<xhtml:link rel="alternate" hreflang="x-default" href="${escape(absoluteUrl(u.alternates[X_DEFAULT_LOCALE]!))}"/>`]
            : [],
        )
        .join("");
      const lastmod = u.lastmod ? `<lastmod>${new Date(u.lastmod).toISOString()}</lastmod>` : "";
      return `<url><loc>${escape(absoluteUrl(u.path))}</loc>${lastmod}${links}</url>`;
    })
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${body}\n</urlset>\n`;
}

export function sitemapIndex(files: string[]): string {
  const body = files.map((f) => `<sitemap><loc>${escape(absoluteUrl(`/sitemaps/${f}`))}</loc></sitemap>`).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</sitemapindex>\n`;
}

/** API alternates (no prefix) -> prefixed paths. */
export function prefixAlternates(alternates: Partial<Record<Locale, string>>): Partial<Record<Locale, string>> {
  return Object.fromEntries(LOCALES.filter((l) => alternates[l] !== undefined).map((l) => [l, prefixed(l, alternates[l]!)]));
}

export function xmlResponse(xml: string): Response {
  return new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=3600, s-maxage=3600" },
  });
}
