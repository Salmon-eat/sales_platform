import type { MetadataRoute } from "next";

import { LOCALES } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import { SITE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  const accounts = LOCALES.map((l) => localizedPath(l, { type: "static", key: "account" }));
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/admin", "/v1", "/go/", ...accounts] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
