import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { Fragment, type ReactNode } from "react";

import { RangeFilter } from "./RangeFilter";

import type { Linker, ListState } from "@/lib/list-url";
import { isJobsSection } from "@/lib/sections";
import { get, isActive, type Pairs, setParam, toggleValue } from "@/lib/search-url";
import type { FacetGroup, NamedSlug, SearchResponse } from "@/lib/types";

const VISIBLE_TIER2_GROUPS = 4; // spec §5: tier 2 collapses after 4 items
const PRIORITY = [
  "price",
  "a.year",
  "a.km",
  "salary_min",
  "a.documents",
  "a.suitable_for",
  "schedule",
  "a.team_language",
  "a.housing_cost",
  "a.benefits",
  "contract",
  "radius",
];

type Props = { data: SearchResponse; pairs: Pairs; state: ListState; link: Linker };

export async function FiltersPanel({ data, pairs, state, link }: Props) {
  const t = await getTranslations("search");
  const locale = await getLocale();
  const tier2 = data.facets.filter((g) => g.tier === 2);
  const tier3 = data.facets.filter((g) => g.tier === 3);
  const noLocation = setParam(pairs, "radius", null);

  function facetLink(key: string, value: string, mode: FacetGroup["type"]): string {
    // "with housing" is a path segment (spec §6), everything else stays in the query
    if (key === "housing") return link({ feature: state.feature ? null : "housing" }, pairs);
    return link({}, toggleValue(pairs, key, value, mode));
  }
  function active(key: string, value: string, mode: FacetGroup["type"]): boolean {
    return key === "housing" ? state.feature === "housing" : isActive(pairs, key, value, mode);
  }

  function valueLabel(group: FacetGroup, value: string, label: string | null): string {
    // attributes and section tags (a.<key>) come with labels from the dictionary
    if (group.key.startsWith("a.")) return label ?? group.label ?? t("yes");
    if (group.type === "bool") return t(group.key as "housing");
    if (group.key === "salary_min") return t("salaryValue", { amount: value });
    if (group.key === "radius") return t("radiusValue", { km: value });
    return t(`${group.key}_${value}` as "schedule_full");
  }

  // spec §11 mockup: yes/no conditions are switches, single-choice values are segmented pills, tier 3 are chips
  const variant = (group: FacetGroup) =>
    group.tier === 3 ? "pills" : group.type === "bool" ? "switch" : group.type === "single" ? "segmented" : "check";

  function Item({
    group,
    value,
    label,
    count,
    look,
  }: {
    group: FacetGroup;
    value: string;
    label: string;
    count: number;
    look?: ReturnType<typeof variant>;
  }) {
    const on = active(group.key, value, group.type);
    const kind = look ?? variant(group);
    return (
      <li>
        <Link
          href={facetLink(group.key, value, group.type)}
          scroll={false}
          className={`facet facet--${kind} ${on ? "facet--active" : ""} ${count === 0 && !on ? "facet--zero" : ""}`}
          aria-current={on ? "true" : undefined}
          rel={group.key === "housing" ? undefined : "nofollow"}
        >
          {kind === "check" && <span className="facet-mark" aria-hidden />}
          <span className="facet-label">{label}</span>
          <span className="facet-count">{count}</span>
          {kind === "switch" && <span className="facet-switch" aria-hidden />}
        </Link>
      </li>
    );
  }

  /** Values with vacancies (and the chosen ones) are shown; the empty ones wait behind "show N more". */
  function Split({ items }: { items: { key: string; zero: boolean; node: ReactNode }[] }) {
    const shown = items.filter((i) => !i.zero);
    const hidden = items.filter((i) => i.zero);
    return (
      <>
        <ul>{shown.map((i) => <Fragment key={i.key}>{i.node}</Fragment>)}</ul>
        {hidden.length > 0 && (
          <details className="facet-zero">
            <summary>{t("showMore", { count: hidden.length })}</summary>
            <ul>{hidden.map((i) => <Fragment key={i.key}>{i.node}</Fragment>)}</ul>
          </details>
        )}
      </>
    );
  }

  function Group({ group }: { group: FacetGroup }) {
    if (group.type === "range") {
      // no ad has this number yet (spare parts have no mileage): nothing to narrow
      if (group.min === null && group.chosen_from === null && group.chosen_to === null) return null;
      return (
        <RangeFilter
          param={group.key}
          label={group.label ?? t(group.key as "price")}
          unit={group.key === "price" ? "€" : group.unit}
          min={group.min}
          max={group.max}
          from={group.chosen_from}
          to={group.chosen_to}
          base={link({}, setParam(pairs, group.key, null))}
          locale={locale}
        />
      );
    }
    const items = group.values.map((v) => ({
      key: v.value,
      zero: v.count === 0 && !active(group.key, v.value, group.type),
      node: <Item group={group} value={v.value} label={valueLabel(group, v.value, v.label)} count={v.count} />,
    }));
    if (items.every((i) => i.zero)) return null; // nothing to pick here right now
    return (
      <div className={`facet-group facet-group--${variant(group)}`}>
        <h3>{group.label ?? t(group.key as "schedule")}</h3>
        <Split items={items} />
      </div>
    );
  }

  // switches on top: "new" first, then yes/no conditions (housing, no language…)
  const posted = tier2.find((g) => g.key === "posted" && g.values.length > 0);
  const bools = [...(posted ? [posted] : []), ...tier2.filter((g) => g.type === "bool")];
  // the first four blocks stay open (spec §5); for this audience documents and "suitable for" matter
  // more than schedule or contract
  const rank = (key: string) => {
    const i = PRIORITY.indexOf(key);
    return i === -1 ? PRIORITY.length : i;
  };
  // price, year and kilometres stand right under the categories, as on every car and classifieds site
  const ranges = tier2.filter((g) => g.type === "range").sort((a, b) => rank(a.key) - rank(b.key));
  const others = tier2
    .filter((g) => g.type !== "bool" && g.type !== "range" && g.key !== "posted")
    .sort((a, b) => rank(a.key) - rank(b.key));
  const blocks: ({ kind: "bools" } | { kind: "group"; group: FacetGroup })[] = [
    ...(bools.length ? [{ kind: "bools" as const }] : []),
    ...others.map((group) => ({ kind: "group" as const, group })),
  ];
  const visible = VISIBLE_TIER2_GROUPS;
  const renderBlock = (block: (typeof blocks)[number]) =>
    block.kind === "bools" ? (
      <div key="bools" className="facet-group facet-group--switch">
        <Split
          items={bools.map((g) => {
            const value = g.key === "posted" ? g.values[0].value : "1";
            const count = g.values[0]?.count ?? 0;
            return {
              key: g.key,
              zero: count === 0 && !active(g.key, value, g.type),
              node:
                g.key === "posted" ? (
                  <Item group={g} value={value} label={t("posted_3d")} count={count} look="switch" />
                ) : (
                  <Item group={g} value={value} label={g.label ?? t(g.key as "housing")} count={count} />
                ),
            };
          })}
        />
      </div>
    ) : (
      <Group key={block.group.key} group={block.group} />
    );

  const jobs = isJobsSection(state.section.key);
  const categoryBlock = tier3.length > 0 && data.category && (
    <div className="facet-block facet-block--category">
      <h2>{t("attributes", { category: data.category.name })}</h2>
      {tier3.map((g) => (
        <Group key={g.key} group={g} />
      ))}
    </div>
  );

  // tier 1: which categories are listed depends on what is selected
  const selected = state.profession ?? state.sector;
  const categoryLink = (c: NamedSlug, isSelected: boolean) => {
    if (!state.sector) return link({ sector: isSelected ? null : c }, pairs); // sectors
    if (isSelected) return state.profession ? link({ profession: null }, pairs) : link({ sector: null }, pairs);
    return link({ profession: c }, pairs); // professions of the sector
  };

  return (
    <div className="filters">
      <h2 className="filters-title">{t("filters")}</h2>
      <div className="facet-group facet-group--check">
        {/* professions in the jobs section, categories (dogs, flats, vans) everywhere else */}
        <h3>{t(jobs ? "categories" : "categoriesAds")}</h3>
        <ul>
          {selected && (
            <li>
              <Link
                href={state.profession ? link({ profession: null }, pairs) : link({ sector: null }, pairs)}
                scroll={false}
                className="facet facet--back"
              >
                ← {state.profession ? state.sector?.name : t(jobs ? "allCategories" : "allCategoriesAds")}
              </Link>
            </li>
          )}
        </ul>
        <Split
          items={data.categories.map((c) => ({
            key: String(c.id),
            zero: c.count === 0 && !c.selected,
            node: (
              <li>
                <Link
                  href={categoryLink({ key: c.key, slug: c.slug, name: c.name }, c.selected)}
                  scroll={false}
                  className={`facet facet--check ${c.selected ? "facet--active" : ""} ${c.count === 0 && !c.selected ? "facet--zero" : ""}`}
                >
                  <span className="facet-mark" aria-hidden />
                  <span className="facet-label">{c.name}</span>
                  <span className="facet-count">{c.count}</span>
                </Link>
              </li>
            ),
          }))}
        />
      </div>

      {ranges.map((g) => (
        <Group key={g.key} group={g} />
      ))}
      {/* a car is chosen by its make before its town; a job by its town first */}
      {!jobs && categoryBlock}

      <div className="facet-group facet-group--check">
        <h3>{t("places")}</h3>
        <ul>
          {state.location && (
            <li>
              <Link href={link({ location: null }, noLocation)} scroll={false} className="facet facet--back">
                ← {t("allPlaces")}
              </Link>
            </li>
          )}
          {data.places.slice(0, 10).map((p) => (
            <li key={p.slug}>
              <Link
                href={link({ location: p.selected ? null : p.slug }, noLocation)}
                scroll={false}
                className={`facet facet--check ${p.selected ? "facet--active" : ""}`}
              >
                <span className="facet-mark facet-mark--radio" aria-hidden />
                <span className="facet-label">{p.name}</span>
                <span className="facet-count">{p.count}</span>
              </Link>
            </li>
          ))}
        </ul>
        {data.spain_wide > 0 && <p className="facet-note">{t("spainWideNote", { count: data.spain_wide })}</p>}
      </div>

      {jobs && categoryBlock}

      {blocks.slice(0, visible).map(renderBlock)}
      {blocks.length > visible && (
        <details
          className="facet-more"
          open={blocks.slice(visible).some((b) => b.kind === "group" && get(pairs, b.group.key))}
        >
          <summary>{t("moreFilters")}</summary>
          {blocks.slice(visible).map(renderBlock)}
        </details>
      )}
    </div>
  );
}
