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
import { isJobsSection, sectionUi } from "@/lib/sections";
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
                // pointed at or tabbed to: fetch the panel's numbers now, so the click opens it full
                onPointerEnter={() => sectionUi(section.key).picker && void warmUp(section.key, locale)}
                onFocus={() => sectionUi(section.key).picker && void warmUp(section.key, locale)}
                aria-expanded={sectionUi(section.key).picker ? isOpen : undefined}
              >
                {inside}
                {sectionUi(section.key).picker && <ChevronDown className="section-card__chevron" size={20} aria-hidden />}
              </Link>
            </li>
            {/* a full-width row placed after the card; the grid packs the rest of the card's row back in
                front of it (grid-auto-flow: dense), so it always opens under the whole row */}
            {isOpen && (
              <li className="section-grid__panel">
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

/** The counts for a choice: the list with it applied, and the category tiles counted without a category
 * (choosing one must not hide the others). One search each, one ad per page: only the numbers matter. */
function loadCounts(
  sectionKey: string,
  locale: string,
  category: string | null,
  place: string | null,
  pairs: Pairs,
  signal?: AbortSignal,
): Promise<Counts> {
  const ask = (query: Pairs) => {
    const qs = new URLSearchParams([["lang", locale], ["section", sectionKey], ["per_page", "1"], ...query]);
    return fetch(`/v1/listings?${qs}`, { signal }).then((r) =>
      r.ok ? (r.json() as Promise<SearchResponse>) : Promise.reject(new Error(String(r.status))),
    );
  };
  return Promise.all([ask(queryOf(category, place, pairs)), ask(queryOf(null, place, pairs))]).then(([current, tiles]) => ({
    current,
    tiles: tiles.categories,
  }));
}

/** Answers for a panel with nothing chosen, asked for as soon as the card is pointed at, so the click
 * opens a full panel at once. A failed one is dropped, so the next attempt asks again. */
const warm = new Map<string, Promise<Counts>>();

function warmUp(sectionKey: string, locale: string): Promise<Counts> {
  const key = `${locale}|${sectionKey}`;
  let answer = warm.get(key);
  if (!answer) {
    answer = loadCounts(sectionKey, locale, null, null, []);
    answer.catch(() => warm.delete(key));
    warm.set(key, answer);
  }
  return answer;
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
  const ui = sectionUi(section.key);

  const [category, setCategory] = useState<string | null>(null);
  const [place, setPlace] = useState<string | null>(null);
  const [pairs, setPairs] = useState<Pairs>([]);
  const [counts, setCounts] = useState<Counts | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const pristine = !category && !place && pairs.length === 0;
    const load = () =>
      // nothing chosen yet: the answer warmed up when the card was pointed at, if it came in time
      (pristine ? warmUp(section.key, locale) : loadCounts(section.key, locale, category, place, pairs, controller.signal))
        .then((next) => !controller.signal.aborted && setCounts(next))
        .catch(() => undefined);
    // the first answer at once; after that wait for the clicking to pause
    const timer = setTimeout(load, counts ? DEBOUNCE_MS : 0);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // `counts` only decides the delay; a new answer must not ask again
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, place, pairs, locale, section.key]);

  const target = (() => {
    const qs = new URLSearchParams(queryOf(category, place, pairs)).toString().replace(/%2C/gi, ",");
    return `${prefixed(locale, section.slug)}${qs ? `?${qs}` : ""}`;
  })();

  // once it is on screen, bring it into view if it opened under a row low on the screen
  const box = useRef<HTMLDivElement>(null);
  const shown = counts !== null;
  useEffect(() => {
    if (shown) box.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [shown]);

  // nothing to show until the first counts are in: the panel then slides open whole, never half-empty
  if (!counts) return null;

  const groupsOf = (keys: string[]) =>
    keys.map((key) => counts.current.facets.find((g) => g.key === key)).filter((g): g is FacetGroup => Boolean(g));
  const chip = (g: FacetGroup, value: string, label: string, count: number) => (
    <PickerChip
      key={`${g.key}:${value}`}
      label={label}
      count={count}
      chosen={isActive(pairs, g.key, value, g.type)}
      onToggle={() => setPairs((current) => toggleValue(current, g.key, value, g.type))}
    />
  );
  /** Yes/no filters in one row (under `rowTitle`, if any), then each list of values under its name. */
  const renderGroups = (keys: string[], rowTitle: string | null) => {
    const groups = groupsOf(keys);
    const yesNo = groups.filter((g) => g.type === "bool");
    const lists = groups.filter((g) => g.type !== "bool" && g.type !== "range");
    return (
      <>
        {yesNo.length > 0 && (
          <section className="picker__group">
            {rowTitle && <h3>{rowTitle}</h3>}
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
      </>
    );
  };
  const more = ui.pickerMore ?? [];

  return (
    <div ref={box} className="picker" role="region" aria-labelledby="picker-title">
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

        {renderGroups(ui.picker ?? [], tHome("pickerMain"))}

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

        {/* languages and papers: open to everyone, folded for those who do not need them. The language
            the site is read in says nothing about somebody's papers, so nothing here is guessed */}
        {more.length > 0 && (
          <details className="picker__more" open={pairs.some(([key]) => more.includes(key))}>
            <summary>{tHome("pickerMore")}</summary>
            {renderGroups(more, null)}
          </details>
        )}
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
          {tHome("pickerShow", { found: t(jobs ? "found" : "foundAds", { count: counts.current.total }) })}
        </button>
      </footer>
    </div>
  );
}
