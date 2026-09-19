import "server-only";

import type { Locale } from "@/i18n/routing";

import { getPopularLocations, getTaxonomy, orFallback } from "./api";
import type { ApplicationOptions, CategoryNode, Taxonomy } from "./types";

const EMPTY: Taxonomy = { sections: [] };

/** Sectors of the jobs section and popular cities for the application form. */
export async function getApplicationOptions(lang: string): Promise<ApplicationOptions & { taxonomy: Taxonomy }> {
  const [taxonomy, cities] = await Promise.all([
    orFallback(getTaxonomy(lang), EMPTY),
    orFallback(getPopularLocations(lang, 50), []),
  ]);
  const jobs = taxonomy.sections.find((s) => s.key === "empleo");
  return {
    taxonomy,
    sectors: (jobs?.categories ?? []).map((c) => ({ id: c.id, name: c.name })),
    cities: cities.map((c) => ({ slug: c.slug, name: c.name })),
  };
}

export function findCategory(taxonomy: Taxonomy, esSlug: string): CategoryNode | undefined {
  const walk = (nodes: CategoryNode[]): CategoryNode | undefined => {
    for (const node of nodes) {
      if (node.slugs.es === esSlug) return node;
      const found = walk(node.children);
      if (found) return found;
    }
    return undefined;
  };
  return walk(taxonomy.sections.flatMap((s) => s.categories));
}

/** Path of an agency service page ("posluhy/kod-95"): services are flat, without the sector. */
export function servicePath(taxonomy: Taxonomy, locale: Locale, esSlug: string): string | null {
  for (const section of taxonomy.sections.filter((s) => s.kind === "services")) {
    for (const sector of section.categories) {
      const service = sector.children.find((c) => c.slugs.es === esSlug);
      if (service) return `${section.slugs[locale]}/${service.slugs[locale]}`;
    }
  }
  return null;
}

/** Canonical list path of a category ("robota/transport/vodii-ce"), without the language prefix. */
export function categoryPath(taxonomy: Taxonomy, locale: Locale, esSlug: string): string | null {
  const walk = (nodes: CategoryNode[], trail: string[]): string[] | null => {
    for (const node of nodes) {
      const here = [...trail, node.slugs[locale]];
      if (node.slugs.es === esSlug) return here;
      const found = walk(node.children, here);
      if (found) return found;
    }
    return null;
  };
  for (const section of taxonomy.sections) {
    const found = walk(section.categories, [section.slugs[locale]]);
    if (found) return found.join("/");
  }
  return null;
}
