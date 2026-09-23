"use client";

import { MapPin, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { asLocale } from "@/i18n/routing";
import { track } from "@/lib/analytics";
import { localizedPath, prefixed } from "@/lib/routes";
import type { HomeSection, LocationRef } from "@/lib/types";

type Props = { sections: HomeSection[] };

/** The one search of the whole site: what, in which section, where. */
export function AdSearch({ sections }: Props) {
  const t = useTranslations("home");
  const ts = useTranslations("search");
  const locale = asLocale(useLocale());
  const router = useRouter();
  const [section, setSection] = useState("");
  const [place, setPlace] = useState<LocationRef | null>(null);
  const [cities, setCities] = useState<LocationRef[]>([]);
  const [cityMenu, setCityMenu] = useState(false);
  const box = useRef<HTMLFormElement>(null);

  useEffect(() => {
    fetch(`/v1/locations/popular?lang=${locale}&limit=30`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setCities)
      .catch(() => undefined);
  }, [locale]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setCityMenu(false);
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
        <input name="q" type="search" autoComplete="off" placeholder={t("searchPlaceholder")} aria-label={t("searchPlaceholder")} />
      </label>
      <label className="ad-search__field ad-search__section">
        <select value={section} onChange={(e) => setSection(e.target.value)} aria-label={t("allSectionsOption")}>
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
