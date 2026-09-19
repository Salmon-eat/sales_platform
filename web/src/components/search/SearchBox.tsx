"use client";

import { MapPin, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";

import { track } from "@/lib/analytics";
import type { LocationRef, SuggestResponse } from "@/lib/types";

type Place = { slug: string; name: string };

type Props = {
  /** section key -> localized path, e.g. { empleo: "/ua/robota", servicios: "/ua/posluhy" } */
  sectionPaths: Record<string, string>;
  initialQuery?: string;
  initialPlace?: Place | null;
};

const DEBOUNCE_MS = 150; // spec §7

/**
 * "What + where + Search" block (spec §11). Links use ?category=&location=; the list page turns them
 * into the canonical path (/robota/transport/vodii-ce/madrid) with a single 301.
 */
export function SearchBox({ sectionPaths, initialQuery = "", initialPlace = null }: Props) {
  const t = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const workPath = sectionPaths.empleo;

  const [query, setQuery] = useState(initialQuery);
  const [place, setPlace] = useState<Place | null>(initialPlace);
  const [suggestions, setSuggestions] = useState<SuggestResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [cityMenu, setCityMenu] = useState(false);
  const [cities, setCities] = useState<LocationRef[]>([]);
  const box = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setSuggestions(null);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/v1/suggest?q=${encodeURIComponent(q)}&lang=${locale}`, { signal: controller.signal });
        if (res.ok) setSuggestions(await res.json());
      } catch {
        /* aborted */
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, locale]);

  useEffect(() => {
    function close(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) {
        setOpen(false);
        setCityMenu(false);
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    if (!cityMenu || cities.length) return;
    fetch(`/v1/locations/popular?lang=${locale}&limit=30`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setCities)
      .catch(() => {});
  }, [cityMenu, cities.length, locale]);

  function go(path: string, entries: [string, string | null | undefined][]) {
    const qs = new URLSearchParams();
    for (const [k, v] of entries.sort(([a], [b]) => a.localeCompare(b))) if (v) qs.set(k, v);
    const search = qs.toString().replace(/%2C/gi, ",");
    setOpen(false);
    setCityMenu(false);
    router.push(search ? `${path}?${search}` : path);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) track("search", { props: { q: query.trim().slice(0, 100), city: place?.slug ?? "" } });
    go(workPath, [
      ["q", query.trim()],
      ["location", place?.slug],
    ]);
  }

  // an agency service (documents, training) is a page of its own, not a list of listings
  const isService = (sectionKey: string) => sectionKey === "servicios";
  const openCategory = (sectionKey: string, slug: string, location?: string | null) =>
    isService(sectionKey)
      ? go(`${sectionPaths.servicios}/${slug}`, [])
      : go(sectionPaths[sectionKey] ?? workPath, [["category", slug], ["location", location]]);

  const has = suggestions && (suggestions.professions.length || suggestions.places.length || suggestions.combos.length);

  return (
    <form ref={box} className="search-box" role="search" onSubmit={onSubmit}>
      <label className="search-box-field">
        <Search size={18} aria-hidden />
        <input
          name="q"
          type="search"
          value={query}
          autoComplete="off"
          placeholder={t("header.searchPlaceholder")}
          aria-label={t("header.searchPlaceholder")}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
      </label>
      <button
        type="button"
        className="search-box-field search-box-where"
        onClick={() => setCityMenu((v) => !v)}
        aria-expanded={cityMenu}
        aria-label={t("search.where")}
      >
        <MapPin size={18} aria-hidden />
        <span>{place?.name ?? t("search.allPlaces")}</span>
      </button>
      <button type="submit" className="btn btn--primary search-box-submit">
        {t("search.submit")}
      </button>

      {open && has ? (
        <div className="suggest" role="listbox">
          {suggestions.combos.length > 0 && (
            <SuggestGroup title={t("search.suggestCombos")}>
              {suggestions.combos.map((c) => (
                <button
                  key={`${c.category.slug}-${c.place.slug}`}
                  type="button"
                  onClick={() => openCategory(c.category.section_key, c.category.slug, c.place.slug)}
                >
                  <span>
                    {c.category.name} · {c.place.name}
                  </span>
                  <small>{t("search.suggestCount", { count: c.count })}</small>
                </button>
              ))}
            </SuggestGroup>
          )}
          {suggestions.professions.length > 0 && (
            <SuggestGroup title={t("search.suggestProfessions")}>
              {suggestions.professions.map((p) => (
                <button
                  key={p.slug}
                  type="button"
                  onClick={() => openCategory(p.section_key, p.slug, place?.slug)}
                >
                  <span>{p.name}</span>
                  <small>{isService(p.section_key) ? t("services.catalogTitle") : t("search.suggestCount", { count: p.count })}</small>
                </button>
              ))}
            </SuggestGroup>
          )}
          {suggestions.places.length > 0 && (
            <SuggestGroup title={t("search.suggestPlaces")}>
              {suggestions.places.map((p) => (
                <button key={p.slug} type="button" onClick={() => go(workPath, [["location", p.slug]])}>
                  <span>
                    {p.name}
                    {p.parent_name && <em> · {p.parent_name}</em>}
                  </span>
                  <small>{t("search.suggestCount", { count: p.count })}</small>
                </button>
              ))}
            </SuggestGroup>
          )}
          <button type="submit" className="suggest-all">
            {t("search.searchIn", { q: query.trim() })}
          </button>
        </div>
      ) : null}

      {cityMenu && (
        <div className="suggest suggest--cities">
          <SuggestGroup title={t("search.places")}>
            <button
              type="button"
              onClick={() => {
                setPlace(null);
                setCityMenu(false);
              }}
            >
              <span>{t("search.allPlaces")}</span>
            </button>
            {cities.map((c) => (
              <button
                key={c.slug}
                type="button"
                onClick={() => {
                  setPlace({ slug: c.slug, name: c.name });
                  setCityMenu(false);
                }}
              >
                <span>{c.name}</span>
              </button>
            ))}
          </SuggestGroup>
        </div>
      )}
    </form>
  );
}

function SuggestGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="suggest-group">
      <div className="suggest-title">{title}</div>
      {children}
    </div>
  );
}
