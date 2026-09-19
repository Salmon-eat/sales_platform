"use client";

import { Briefcase, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type KeyboardEvent, useId, useMemo, useState } from "react";

import type { AdminSection } from "@/lib/types";

type Props = {
  sections: AdminSection[];
  value: number | null;
  onChange: (id: number | null) => void;
  disabled?: boolean;
};

type Entry = { id: number; sector: string; name: string; section: string | null; search: string };

const JOBS_SECTION = "empleo";

const fold = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

/** Professions (and sectors without professions) found by name in any language or by synonym:
 * "хост" -> Хостес, "дальнобійник" -> Водій CE, "camarero" -> Офіціант. */
export function CategoryPicker({ sections, value, onChange, disabled }: Props) {
  const t = useTranslations("admin.listings");
  const locale = useLocale();
  const id = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const entries = useMemo(() => {
    const out: Entry[] = [];
    // agency services (documents, training) are not listings: they have their own pages
    for (const section of sections.filter((s) => s.kind === "listings")) {
      const sectionName = section.name[locale] || section.name.es;
      // the jobs section is the default one: not repeated on every row
      const sectionLabel = !section.is_enabled
        ? t("category.sectionOff", { section: sectionName })
        : section.key === JOBS_SECTION
          ? null
          : sectionName;
      for (const sector of section.categories) {
        const nodes = sector.children.length ? sector.children : [sector];
        for (const node of nodes) {
          // a disabled section (Житло) is hidden on the site: offer it only to a listing already there
          if (!section.is_enabled && node.id !== value) continue;
          const words = [
            ...Object.values(node.name),
            ...Object.values(node.synonyms ?? {}).flat(),
            ...(node === sector ? [] : Object.values(sector.name)),
          ];
          out.push({
            id: node.id,
            sector: node === sector ? "" : sector.name[locale] || sector.name.es,
            name: node.name[locale] || node.name.es,
            section: sectionLabel,
            search: fold(words.join(" ")),
          });
        }
      }
    }
    return out;
  }, [sections, value, locale, t]);

  const selected = entries.find((e) => e.id === value);
  const words = fold(query).split(/\s+/).filter(Boolean);
  const matches = words.length ? entries.filter((e) => words.every((w) => e.search.includes(w))) : entries;

  function pick(entry: Entry | undefined) {
    if (!entry) return;
    onChange(entry.id);
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, matches.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault(); // do not submit the listing form
      pick(matches[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  if (selected) {
    return (
      <div className="location-chosen">
        <Briefcase size={16} aria-hidden />
        <span>
          {selected.sector && <span className="muted">{selected.sector} › </span>}
          <strong>{selected.name}</strong>
        </span>
        {!disabled && (
          <button type="button" className="icon-btn" aria-label={t("category.change")} onClick={() => onChange(null)}>
            <X size={16} />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="location-picker">
      <input
        id={id}
        value={query}
        disabled={disabled}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        placeholder={t("category.placeholder")}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
      />
      {open && (
        <ul className="location-options category-options" id={`${id}-list`} role="listbox">
          {matches.length === 0 && <li className="muted small category-empty">{t("category.noMatches")}</li>}
          {matches.map((entry, i) => (
            <li key={entry.id} role="option" aria-selected={i === active}>
              <button
                type="button"
                className={i === active ? "is-active" : undefined}
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(entry)}
              >
                <strong>{entry.name}</strong>
                <span className="muted small">
                  {" "}
                  · {entry.sector || t("category.sector")}
                  {entry.section && `, ${entry.section}`}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
