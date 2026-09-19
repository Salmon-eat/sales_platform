"use client";

import { MapPin, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useState } from "react";

import type { AdminLocation, LocationBrief, Page } from "@/lib/types";

type Props = {
  value: LocationBrief | null;
  onChange: (value: LocationBrief | null) => void;
  disabled?: boolean;
};

/** Municipalities and villages by any name (es, co-official, Cyrillic, transliteration). */
export function LocationPicker({ value, onChange, disabled }: Props) {
  const t = useTranslations("admin.listings");
  const locale = useLocale();
  const id = useId();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<AdminLocation[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setItems([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ q, per_page: "8" });
        qs.append("level", "municipio");
        qs.append("level", "localidad");
        // the API takes the session only in the Authorization header: go through the Next.js server
        const res = await fetch(`/admin/api/locations?${qs}`, { signal: controller.signal });
        if (res.ok) setItems(((await res.json()) as Page<AdminLocation>).items);
      } catch {
        /* aborted */
      }
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  if (value) {
    return (
      <div className="location-chosen">
        <MapPin size={16} aria-hidden />
        <span>
          <strong>{value.name}</strong>
          {value.parent_name && <span className="muted"> · {value.parent_name}</span>}
          {value.level === "localidad" && <span className="muted"> {t("location.villageMark")}</span>}
        </span>
        {!disabled && (
          <button type="button" className="icon-btn" aria-label={t("location.change")} onClick={() => onChange(null)}>
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
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={t("location.placeholder")}
        autoComplete="off"
        role="combobox"
        aria-expanded={open && items.length > 0}
        aria-controls={`${id}-list`}
      />
      {open && items.length > 0 && (
        <ul className="location-options" id={`${id}-list`} role="listbox">
          {items.map((item) => {
            const name = item.names[locale] || item.names.es;
            return (
              <li key={item.id} role="option" aria-selected={false}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onChange({ id: item.id, level: item.level, slug: item.slug, name, parent_name: item.parent_name });
                    setQuery("");
                  }}
                >
                  <strong>{name}</strong>
                  {name !== item.names.es && <span className="muted"> ({item.names.es})</span>}
                  <span className="muted small">
                    {" "}
                    · {item.level === "localidad" ? t("location.village") : t("location.municipality")}
                    {item.parent_name && `, ${item.parent_name}`}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
