import type { MetadataRoute } from "next";

import { LOCALES } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import { SITE_URL } from "@/lib/seo";

/**
 * Crawlers that only collect text to train models: they take the employers' listings and send nobody back.
 * Search engines and the assistants that answer with a link to us stay welcome (that brings candidates).
 */
const AI_TRAINING_BOTS = [
  "GPTBot",
  "OAI-SearchBot",
  "ClaudeBot",
  "anthropic-ai",
  "Google-Extended",
  "Applebot-Extended",
  "Meta-ExternalAgent",
  "FacebookBot",
  "Bytespider",
  "Amazonbot",
  "CCBot",
  "cohere-ai",
  "Diffbot",
  "omgili",
  "ImagesiftBot",
  "PanguBot",
  "Timpibot",
  "Webzio-Extended",
];

export default function robots(): MetadataRoute.Robots {
  const accounts = LOCALES.map((l) => localizedPath(l, { type: "static", key: "account" }));
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: ["/admin", "/v1", "/go/", ...accounts] },
      { userAgent: AI_TRAINING_BOTS, disallow: "/" },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
