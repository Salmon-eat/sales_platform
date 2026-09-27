import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { facetValueLabel } from "@/lib/facets";
import { type Linker, type ListState, makeFacetLinks } from "@/lib/list-url";
import type { Pairs } from "@/lib/search-url";
import { forAudience, sectionUi } from "@/lib/sections";
import type { SearchResponse } from "@/lib/types";

type Props = { data: SearchResponse; pairs: Pairs; state: ListState; link: Linker };

/**
 * One-click filters above the list ("With housing", "No experience", "Part-time"…), the way Jobtoday
 * does it: the ones people reach for most, without opening the panel. Which ones is section data
 * (SECTION_UI); each shows how many ads it leaves and is left out while it would leave none.
 */
export async function QuickFilters({ data, pairs, state, link }: Props) {
  const locale = await getLocale();
  const choices = forAudience(state.section.key, locale, sectionUi(state.section.key).quick ?? [], ([key]) => key);
  if (choices.length === 0) return null;
  const t = await getTranslations("search");
  const facets = makeFacetLinks(link, state, pairs);

  const buttons = choices.flatMap(([key, value]) => {
    const group = data.facets.find((g) => g.key === key);
    const option = group?.values.find((v) => v.value === value);
    if (!group || !option) return [];
    const on = facets.active(key, value, group.type);
    if (option.count === 0 && !on) return [];
    return [{ key: `${key}:${value}`, group, value, count: option.count, on, label: facetValueLabel(group, value, option.label, t) }];
  });
  if (buttons.length === 0) return null;

  return (
    <nav className="quick-filters" aria-label={t("quickFilters")}>
      {buttons.map((b) => (
        <Link
          key={b.key}
          href={facets.href(b.group.key, b.value, b.group.type)}
          scroll={false}
          rel="nofollow"
          className={b.on ? "quick-filter quick-filter--on" : "quick-filter"}
          aria-pressed={b.on}
        >
          {b.label}
          <span className="quick-filter__count">{b.count}</span>
        </Link>
      ))}
    </nav>
  );
}
