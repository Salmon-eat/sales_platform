"use client";

import { MapPin, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { announceHeroSection } from "@/components/home/heroEvents";
import { asLocale } from "@/i18n/routing";
import { track } from "@/lib/analytics";
import { localizedPath, prefixed } from "@/lib/routes";
import type { HomeSection, LocationRef, SuggestWord } from "@/lib/types";

type Props = {
  sections: HomeSection[];
  /** what was searched for: on the results page the box shows it back, on the home page it is empty */
  initialQuery?: string;
  initialCity?: string | null;
};

/** The one search of the whole site: what, in which section, where. */
export function AdSearch({ sections, initialQuery = "", initialCity = null }: Props) {
  const t = useTranslations("home");
  const ts = useTranslations("search");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const [section, setSection] = useState("");
  const [place, setPlace] = useState<LocationRef | null>(null);
  const [cities, setCities] = useState<LocationRef[]>([]);
  const [cityMenu, setCityMenu] = useState(false);
  const box = useRef<HTMLFormElement>(null);

  // what is being typed, and the words the site can finish it with
  const [query, setQuery] = useState(initialQuery);
  const [words, setWords] = useState<SuggestWord[]>([]);
  const [wordMenu, setWordMenu] = useState(false);
  const [active, setActive] = useState(-1);

  // going back, or landing on another results page, must not leave the previous word in the box
  useEffect(() => setQuery(initialQuery), [initialQuery]);

  useEffect(() => {
    const text = query.trim();
    if (text.length < 2) {
      setWords([]);
      return;
    }
    // a request per keystroke would be a request per keystroke; wait until the typing pauses
    const timer = setTimeout(() => {
      fetch(`/v1/suggest?lang=${locale}&q=${encodeURIComponent(text)}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data: { words?: SuggestWord[] } | null) => {
          setWords(data?.words ?? []);
          setActive(-1);
        })
        .catch(() => undefined);
    }, 150);
    return () => clearTimeout(timer);
  }, [query, locale]);

  useEffect(() => {
    fetch(`/v1/locations/popular?lang=${locale}&limit=30`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: LocationRef[]) => {
        setCities(list);
        // the town that was searched for keeps its name in the button, not just in the address
        if (initialCity) setPlace(list.find((item) => item.slug === initialCity) ?? null);
      })
      .catch(() => undefined);
  }, [locale, initialCity]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) {
        setCityMenu(false);
        setWordMenu(false);
      }
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  /** A chosen word goes straight to the place it belongs to: that is what the count under it means. */
  function pick(word: SuggestWord) {
    setQuery(word.text);
    setWordMenu(false);
    track("search", { props: { q: word.text.slice(0, 100), picked: word.category } });
    router.push(prefixed(locale, `${word.section_slug}/${word.category_slug}`));
  }

  function onKeys(event: KeyboardEvent<HTMLInputElement>) {
    if (!wordMenu || words.length === 0) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      // -1 means "what I typed myself", and the list wraps around through it
      setActive((i) => {
        const next = i + step;
        if (next < -1) return words.length - 1;
        if (next >= words.length) return -1;
        return next;
      });
    } else if (event.key === "Enter" && active >= 0 && active < words.length) {
      event.preventDefault();
      pick(words[active]);
    } else if (event.key === "Escape") {
      setWordMenu(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWordMenu(false);
    const query = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    if (query) track("search", { props: { q: query.slice(0, 100), city: place?.slug ?? "" } });
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (place) params.set("location", place.slug);
    // a chosen section goes to that section's page; otherwise the search across everything
    const target = section ? prefixed(locale, section) : localizedPath(locale, { type: "search" });
    router.push(`${target}${params.size ? `?${params}` : ""}`);
  }

  return (
    <form ref={box} className="ad-search" role="search" onSubmit={submit}>
      <label className="ad-search__field">
        <Search size={18} aria-hidden />
        <input
          name="q"
          type="search"
          autoComplete="off"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setWordMenu(true);
            setCityMenu(false);
          }}
          onFocus={() => setWordMenu(true)}
          onKeyDown={onKeys}
          placeholder={t("searchPlaceholder")}
          aria-label={t("searchPlaceholder")}
          aria-expanded={wordMenu && words.length > 0}
          role="combobox"
          aria-controls="search-suggestions"
        />
      </label>
      <label className="ad-search__field ad-search__section">
        <select
          value={section}
          onChange={(e) => {
            setSection(e.target.value);
            announceHeroSection(sections.find((s) => s.slug === e.target.value)?.key ?? null);
          }}
          aria-label={t("allSectionsOption")}
        >
          <option value="">{t("allSectionsOption")}</option>
          {sections.map((s) => (
            <option key={s.key} value={s.slug}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="ad-search__field ad-search__where"
        onClick={() => setCityMenu((open) => !open)}
        aria-expanded={cityMenu}
      >
        <MapPin size={18} aria-hidden />
        <span>{place?.name ?? ts("allPlaces")}</span>
      </button>
      <button type="submit" className="btn btn--primary ad-search__submit">
        {t("searchButton")}
      </button>

      {wordMenu && words.length > 0 && (
        <div className="suggest suggest--words" id="search-suggestions" role="listbox">
          <div className="suggest-group">
            <div className="suggest-title">{ts("suggestTitle")}</div>
            {words.map((word, i) => {
              // the part already typed stays plain, the rest is what the site is offering
              const typed = word.text.toLowerCase().startsWith(query.trim().toLowerCase())
                ? query.trim().length
                : 0;
              return (
                <button
                  key={`${word.text}-${word.category_slug}`}
                  type="button"
                  role="option"
                  aria-selected={i === active}
                  className={i === active ? "suggest-word suggest-word--active" : "suggest-word"}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => pick(word)}
                >
                  <span className="suggest-word__text">
                    {typed > 0 && <b>{word.text.slice(0, typed)}</b>}
                    {word.text.slice(typed)}
                    <small>
                      {word.section} / {word.category}
                    </small>
                  </span>
                  <span className="facet-count">{word.count}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {cityMenu && (
        <div className="suggest suggest--cities">
          <div className="suggest-group">
            <div className="suggest-title">{ts("places")}</div>
            <button
              type="button"
              onClick={() => {
                setPlace(null);
                setCityMenu(false);
              }}
            >
              <span>{ts("allPlaces")}</span>
            </button>
            {cities.map((city) => (
              <button
                key={city.slug}
                type="button"
                onClick={() => {
                  setPlace(city);
                  setCityMenu(false);
                }}
              >
                <span>{city.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </form>
  );
}
