/** Links between list pages: tier 1 lives in the path, tiers 2–3 in the query (spec §5, §6). */
import type { Locale } from "@/i18n/routing";

import { prefixed } from "./routes";
import { href, type Pairs } from "./search-url";
import type { NamedSlug } from "./types";

export const FEATURE_SLUGS: Record<"housing", Record<Locale, string>> = {
  housing: { es: "con-alojamiento", en: "with-housing", uk: "z-zhytlom", ru: "s-zhilyom" },
};

export type ListState = {
  section: NamedSlug;
  sector: NamedSlug | null;
  profession: NamedSlug | null;
  feature: "housing" | null;
  location: string | null;
};

export type ListPatch = Partial<Omit<ListState, "section">>;

export function listPath(locale: Locale, state: ListState): string {
  const segments = [
    state.section.slug,
    state.sector?.slug,
    state.profession?.slug,
    state.feature ? FEATURE_SLUGS[state.feature][locale] : null,
    state.location,
  ].filter(Boolean);
  return prefixed(locale, segments.join("/"));
}

/** Builds a link to the same page with some tier-1 parts changed and a new query. */
export function makeLinker(locale: Locale, state: ListState) {
  return (patch: ListPatch, pairs: Pairs = []): string => {
    const next: ListState = { ...state, ...patch };
    if (patch.sector === null) next.profession = null;
    return href(listPath(locale, next), pairs.filter(([k]) => k !== "page"));
  };
}

export type Linker = ReturnType<typeof makeLinker>;
