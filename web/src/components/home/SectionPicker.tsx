"use client";

import { ChevronDown, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type CSSProperties, Fragment, type MouseEvent, type ReactNode, useEffect, useRef, useState } from "react";

import { asLocale } from "@/i18n/routing";
import { facetTitle, facetValueLabel } from "@/lib/facets";
import { prefixed } from "@/lib/routes";
import { isActive, type Pairs, toggleValue } from "@/lib/search-url";
import { forAudience, isJobsSection, sectionUi } from "@/lib/sections";
import type { CategoryFacet, FacetGroup, SearchResponse } from "@/lib/types";

type Section = { key: string; slug: string; name: string };

export type SectionCard = {
  section: Section;
  style?: CSSProperties;
  /** the card's picture and words, drawn on the server */
  inside: ReactNode;
};

/** wait for the clicking to pause before asking for new counts */
const DEBOUNCE_MS = 200;

/**
 * "All sections" on the home page. A section that has a "what are you looking for?" panel (SECTION_UI)
 * slides it open right under its own row, the way OLX does: the other cards stay where they are.
 * Every card stays a real link: a middle click, or a browser without scripts, opens the section.
 */
export function SectionGridList({ cards }: { cards: SectionCard[] }) {
  const locale = asLocale(useLocale());
  const [open, setOpen] = useState<string | null>(null);
  const panel = useRef<HTMLLIElement>(null);

  // bring the panel into view when it opens under a row that is low on the screen
  useEffect(() => {
    if (open) panel.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [open]);

  function onClick(event: MouseEvent, key: string) {
    if (!sectionUi(key).picker) return; // a plain section: just a link
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return; // a new tab
    event.preventDefault();
    setOpen((current) => (current === key ? null : key));
  }

  return (
    <ul className="section-grid">
      {cards.map(({ section, style, inside }) => {
        const isOpen = open === section.key;
        return (
          <Fragment key={section.key}>
            <li>
              <Link
                href={prefixed(locale, section.slug)}
                className={isOpen ? "section-card section-card--open" : "section-card"}
                style={style}
                onClick={(e) => onClick(e, section.key)}
                aria-expanded={sectionUi(section.key).picker ? isOpen : undefined}
              >
                {inside}
                {sectionUi(section.key).picker && <ChevronDown className="section-card__chevron" size={20} aria-hidden />}
              </Link>
            </li>
            {/* a full-width row placed after the card; the grid packs the rest of the card's row back in
                front of it (grid-auto-flow: dense), so it always opens under the whole row */}
            {isOpen && (
              <li ref={panel} className="section-grid__panel">
                <SectionPickerPanel section={section} onClose={() => setOpen(null)} />
              </li>
            )}
          </Fragment>
        );
      })}
    </ul>
  );
}

type Counts = { current: SearchResponse; tiles: CategoryFacet[] };

/** One filter value as a button: how many ads it leaves; hidden while it would leave none. */
function PickerChip({ label, count, chosen, onToggle }: { label: string; count: number; chosen: boolean; onToggle: () => void }) {
  if (count === 0 && !chosen) return null;
  return (
    <button
      type="button"
      className={chosen ? "picker-chip picker-chip--on" : "picker-chip"}
      aria-pressed={chosen}
      onClick={onToggle}
    >
      {label}
      <span className="picker-chip__count">{count}</span>
    </button>
  );
}

/** What is chosen so far, as the list page reads it from the address. */
function queryOf(category: string | null, place: string | null, pairs: Pairs): Pairs {
  return [...(category ? [["category", category] as [string, string]] : []), ...(place ? [["location", place] as [string, string]] : []), ...pairs];
}

/**
 * What the panel holds: the section's categories as tiles, then its filters as buttons (which ones is
 * section data, SECTION_UI), a town, and "Show N" with N counted live while the choice is made. The
 * button leads to the section's list with all of it applied.
 */
function SectionPickerPanel({ section, onClose }: { section: Section; onClose: () => void }) {
  const t = useTranslations("search");
  const tHome = useTranslations("home");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const jobs = isJobsSection(section.key);
  // a Spaniard is not offered "no Spanish needed" or residence papers; a newcomer is
  const groupsShown = forAudience(section.key, locale, sectionUi(section.key).picker ?? [], (key) => key);

  const [category, setCategory] = useState<string | null>(null);
  const [place, setPlace] = useState<string | null>(null);
  const [pairs, setPairs] = useState<Pairs>([]);
  const [counts, setCounts] = useState<Counts | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const ask = (query: Pairs) => {
      const qs = new URLSearchParams([["lang", locale], ["section", section.key], ["per_page", "1"], ...query]);
      return fetch(`/v1/listings?${qs}`, { signal: controller.signal }).then((r) =>
        r.ok ? (r.json() as Promise<SearchResponse>) : Promise.reject(new Error(String(r.status))),
      );
    };
    const timer = setTimeout(() => {
      // the tiles are counted without a category chosen: choosing one must not hide the others
      Promise.all([ask(queryOf(category, place, pairs)), ask(queryOf(null, place, pairs))])
        .then(([current, tiles]) => setCounts({ current, tiles: tiles.categories }))
        .catch(() => undefined);
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [category, place, pairs, locale, section.key]);

  const target = (() => {
    const qs = new URLSearchParams(queryOf(category, place, pairs)).toString().replace(/%2C/gi, ",");
    return `${prefixed(locale, section.slug)}${qs ? `?${qs}` : ""}`;
  })();

  const groups = groupsShown
    .map((key) => counts?.current.facets.find((g) => g.key === key))
    .filter((g): g is FacetGroup => Boolean(g));
  const yesNo = groups.filter((g) => g.type === "bool");
  const lists = groups.filter((g) => g.type !== "bool" && g.type !== "range");
  const chip = (g: FacetGroup, value: string, label: string, count: number) => (
    <PickerChip
      key={`${g.key}:${value}`}
      label={label}
      count={count}
      chosen={isActive(pairs, g.key, value, g.type)}
      onToggle={() => setPairs((current) => toggleValue(current, g.key, value, g.type))}
    />
  );

  return (
    <div className="picker" role="region" aria-labelledby="picker-title">
      <header className="picker__head">
        <h2 id="picker-title">{jobs ? tHome("pickerTitleJobs") : tHome("pickerTitle", { section: section.name })}</h2>
        <button type="button" className="picker__close" aria-label={t("close")} onClick={onClose}>
          <X size={20} aria-hidden />
        </button>
      </header>

      <div className="picker__body">
        <section className="picker__group">
          {/* the tiles are the jobs' fields (Transport, HoReCa), not single professions */}
          <h3>{jobs ? tHome("pickerDirection") : t("categoriesAds")}</h3>
          <div className="picker__tiles">
            {(counts?.tiles ?? []).map((c) => (
              <button
                key={c.slug}
                type="button"
                className={category === c.slug ? "picker-tile picker-tile--on" : "picker-tile"}
                aria-pressed={category === c.slug}
                onClick={() => setCategory((current) => (current === c.slug ? null : c.slug))}
                disabled={c.count === 0 && category !== c.slug}
              >
                <span>{c.name}</span>
                <small>{c.count}</small>
              </button>
            ))}
          </div>
        </section>

        {yesNo.length > 0 && (
          <section className="picker__group">
            <h3>{tHome("pickerMain")}</h3>
            <div className="picker__chips">
              {yesNo.map((g) => chip(g, "1", facetValueLabel(g, "1", null, t), g.values[0]?.count ?? 0))}
            </div>
          </section>
        )}

        {lists.map((g) => (
          <section key={g.key} className="picker__group">
            <h3>{facetTitle(g, t)}</h3>
            <div className="picker__chips">
              {g.values.map((v) => chip(g, v.value, facetValueLabel(g, v.value, v.label, t), v.count))}
            </div>
          </section>
        ))}

        <section className="picker__group">
          <h3>{t("places")}</h3>
          <select className="picker__select" value={place ?? ""} onChange={(e) => setPlace(e.target.value || null)}>
            <option value="">{t("allPlaces")}</option>
            {(counts?.current.places ?? []).map((p) => (
              <option key={p.slug} value={p.slug}>
                {p.name} ({p.count})
              </option>
            ))}
          </select>
        </section>
      </div>

      <footer className="picker__foot">
        <button
          type="button"
          className="btn btn--ghost-dark"
          onClick={() => {
            setCategory(null);
            setPlace(null);
            setPairs([]);
          }}
        >
          {t("reset")}
        </button>
        <button type="button" className="btn btn--primary btn--lg picker__show" onClick={() => router.push(target)}>
          {counts
            ? tHome("pickerShow", { found: t(jobs ? "found" : "foundAds", { count: counts.current.total }) })
            : t("filters")}
        </button>
      </footer>
    </div>
  );
}
