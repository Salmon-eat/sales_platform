"use client";

import { Camera, Check, Loader2, Trash2 } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useMemo, useRef, useState } from "react";

import { actOnAd, type AdInput, deletePhoto, saveAd } from "@/app/[locale]/my-actions";
import { asLocale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";
import type {
  AttributeDef,
  CategoryNode,
  LocationRef,
  MyListingDetail,
  Taxonomy,
} from "@/lib/types";

type Props = {
  taxonomy: Taxonomy;
  cities: (LocationRef & { id: number })[];
  /** the account's name and phone, so nobody types them again */
  defaults: { name: string; phone: string };
  maxPhotos: number;
  days: number;
  /** an ad being edited; absent when writing a new one */
  initial?: MyListingDetail | null;
};

type Photo = { id: number; thumb: string };

const PRICE_KINDS = ["fixed", "negotiable", "free"] as const;
const PERIODS = ["", "month", "week", "day", "hour"] as const;

/** Leaf categories only: a heading with children is not a place for an ad. */
function leaves(nodes: CategoryNode[]): { id: number; name: string; depth: number }[] {
  const out: { id: number; name: string; depth: number }[] = [];
  const walk = (list: CategoryNode[], depth: number) => {
    for (const node of list) {
      if (node.children?.length) {
        out.push({ id: -node.id, name: node.name, depth }); // a heading, not choosable
        walk(node.children, depth + 1);
      } else {
        out.push({ id: node.id, name: node.name, depth });
      }
    }
  };
  walk(nodes, 0);
  return out;
}

function findCategory(nodes: CategoryNode[], id: number): CategoryNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    const inside = node.children?.length ? findCategory(node.children, id) : null;
    if (inside) return inside;
  }
  return null;
}

/** Post an ad: what it is, where, for how much, with photos. Saved as a draft, then sent for checking. */
export function PostAdForm({ taxonomy, cities, defaults, maxPhotos, days, initial }: Props) {
  const t = useTranslations("post");
  const locale = asLocale(useLocale());
  const sections = useMemo(() => taxonomy.sections.filter((s) => s.kind === "listings"), [taxonomy]);

  const startSection = useMemo(
    () =>
      (initial
        ? sections.find((item) => findCategory(item.categories, initial.category_id))?.key
        : undefined) ?? sections[0]?.key ?? "",
    [initial, sections],
  );

  const [sectionKey, setSectionKey] = useState(startSection);
  const [categoryId, setCategoryId] = useState(initial?.category_id ?? 0);
  const [priceKind, setPriceKind] = useState<(typeof PRICE_KINDS)[number]>(
    initial && PRICE_KINDS.includes(initial.price_kind as (typeof PRICE_KINDS)[number])
      ? (initial.price_kind as (typeof PRICE_KINDS)[number])
      : "fixed",
  );
  const [attributes, setAttributes] = useState<Record<string, unknown>>(initial?.attributes ?? {});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<MyListingDetail | null>(initial ?? null);
  const [photos, setPhotos] = useState<Photo[]>(
    (initial?.photos ?? []).map((photo) => ({ id: photo.id, thumb: photo.thumb })),
  );
  const [sent, setSent] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const section = sections.find((s) => s.key === sectionKey);
  const options = useMemo(() => (section ? leaves(section.categories) : []), [section]);
  const category = section && categoryId ? findCategory(section.categories, categoryId) : null;
  const fields: AttributeDef[] = [...(section?.attributes ?? []), ...(category?.attributes ?? [])];

  function setAttribute(key: string, value: unknown) {
    setAttributes((current) => {
      const next = { ...current };
      if (value === "" || value === false || (Array.isArray(value) && !value.length)) delete next[key];
      else next[key] = value;
      return next;
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const price = String(form.get("price") ?? "").trim();
    const input: AdInput = {
      category_id: categoryId,
      location_id: Number(form.get("location_id")),
      lang: locale,
      title: String(form.get("title") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      price: priceKind === "free" || !price ? null : Math.round(Number(price)),
      price_period: String(form.get("price_period") ?? "") || null,
      price_kind: priceKind,
      attributes,
      contact: {
        name: String(form.get("contact_name") ?? "").trim(),
        phone: String(form.get("contact_phone") ?? "").trim(),
      },
    };
    setBusy(true);
    setError(null);
    const result = await saveAd(input, locale, saved?.id);
    setBusy(false);
    if (result.ok) setSaved(result.listing);
    else setError(result.error);
  }

  async function upload(files: FileList | null) {
    if (!files?.length || !saved) return;
    setBusy(true);
    setError(null);
    for (const file of Array.from(files).slice(0, maxPhotos - photos.length)) {
      const response = await fetch(`/api/my/listings/${saved.id}/photos`, {
        method: "POST",
        body: file,
      });
      const body = await response.json().catch(() => null);
      if (response.ok && body) setPhotos((current) => [...current, { id: body.id, thumb: body.thumb }]);
      else setError(body?.detail ?? body?.error ?? "photo_failed");
    }
    setBusy(false);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function removePhoto(id: number) {
    if (!saved) return;
    await deletePhoto(saved.id, id);
    setPhotos((current) => current.filter((photo) => photo.id !== id));
  }

  async function send() {
    if (!saved) return;
    setBusy(true);
    const result = await actOnAd(saved.id, "submit", locale);
    setBusy(false);
    if (result.ok) setSent(true);
    else setError(result.error);
  }

  if (sent) {
    return (
      <div className="post-done">
        <span className="post-done__icon" aria-hidden>
          <Check size={26} />
        </span>
        <h2>{t("sentTitle")}</h2>
        <p className="muted">{t("sentText")}</p>
        <Link
          href={`${localizedPath(locale, { type: "static", key: "account" })}?tab=ads`}
          className="btn btn--primary btn--lg"
        >
          {t("toMyAds")}
        </Link>
      </div>
    );
  }

  return (
    <div className="post-form">
      <form className="post-form__fields" onSubmit={submit}>
        <div className="field-row">
          <label className="field">
            <span>{t("section")}</span>
            <select
              value={sectionKey}
              onChange={(event) => {
                setSectionKey(event.target.value);
                setCategoryId(0);
                setAttributes({});
              }}
            >
              {sections.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("category")}</span>
            <select
              required
              value={categoryId || ""}
              onChange={(event) => {
                setCategoryId(Number(event.target.value));
                setAttributes({});
              }}
            >
              <option value="" disabled>
                {t("categoryPick")}
              </option>
              {options.map((option) =>
                option.id < 0 ? (
                  <option key={option.id} value="" disabled>
                    {"— "}
                    {option.name}
                  </option>
                ) : (
                  <option key={option.id} value={option.id}>
                    {" ".repeat(option.depth * 3)}
                    {option.name}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>

        <label className="field">
          <span>{t("title")}</span>
          <input
            name="title"
            required
            minLength={5}
            maxLength={120}
            defaultValue={saved?.title}
            placeholder={t("titlePlaceholder")}
          />
        </label>

        <label className="field">
          <span>{t("description")}</span>
          <textarea
            name="description"
            required
            minLength={20}
            maxLength={5000}
            rows={6}
            defaultValue={saved?.description}
            placeholder={t("descriptionPlaceholder")}
          />
          <small className="muted">{t("descriptionHint")}</small>
        </label>

        <div className="field-row">
          <label className="field">
            <span>{t("city")}</span>
            <select name="location_id" required defaultValue={saved?.location_id ?? ""}>
              <option value="" disabled>
                {t("cityPick")}
              </option>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>
                  {city.name}
                </option>
              ))}
            </select>
          </label>
          <div className="field">
            <span>{t("price")}</span>
            <div className="price-row">
              <input
                name="price"
                type="number"
                min={0}
                step={1}
                inputMode="numeric"
                disabled={priceKind === "free"}
                defaultValue={saved?.price ?? ""}
                placeholder="€"
              />
              <select name="price_period" defaultValue={saved?.price_period ?? ""}>
                {PERIODS.map((period) => (
                  <option key={period || "once"} value={period}>
                    {t(`period_${period || "once"}`)}
                  </option>
                ))}
              </select>
            </div>
            <div className="chips-row">
              {PRICE_KINDS.map((kind) => (
                <button
                  key={kind}
                  type="button"
                  className={kind === priceKind ? "chip chip--on" : "chip"}
                  onClick={() => setPriceKind(kind)}
                >
                  {t(`kind_${kind}`)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {fields.length > 0 && (
          <fieldset className="post-form__group">
            <legend>{t("details")}</legend>
            {fields.map((field) => (
              <AttributeField
                key={field.key}
                field={field}
                value={attributes[field.key]}
                onChange={(value) => setAttribute(field.key, value)}
              />
            ))}
          </fieldset>
        )}

        <fieldset className="post-form__group">
          <legend>{t("contacts")}</legend>
          <div className="field-row">
            <label className="field">
              <span>{t("yourName")}</span>
              <input name="contact_name" maxLength={200} defaultValue={saved?.contact?.name ?? defaults.name} />
            </label>
            <label className="field">
              <span>{t("phone")}</span>
              <input
                name="contact_phone"
                type="tel"
                defaultValue={saved?.contact?.phone ?? defaults.phone}
                placeholder="+34 600 000 000"
              />
            </label>
          </div>
        </fieldset>

        <button type="submit" className="btn btn--primary btn--lg" disabled={busy || !categoryId}>
          {busy ? <Loader2 size={16} className="spin" aria-hidden /> : null}
          {saved ? t("saveChanges") : t("saveDraft")}
        </button>
        {error && (
          <p className="form-error" role="alert">
            {t.has(`errors.${error}` as "errors.generic")
              ? t(`errors.${error}` as "errors.generic")
              : t("errors.generic")}
          </p>
        )}
      </form>

      <aside className="post-form__photos">
        <h2>{t("photos")}</h2>
        <p className="muted small">{t("photosHint", { count: maxPhotos })}</p>
        {!saved ? (
          <p className="muted small">{t("photosAfterSave")}</p>
        ) : (
          <>
            <ul className="photo-grid">
              {photos.map((photo) => (
                <li key={photo.id}>
                  <img src={photo.thumb} alt="" />
                  <button type="button" onClick={() => removePhoto(photo.id)} aria-label={t("removePhoto")}>
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
              {photos.length < maxPhotos && (
                <li className="photo-grid__add">
                  <label>
                    <Camera size={20} aria-hidden />
                    <span>{t("addPhoto")}</span>
                    <input
                      ref={fileInput}
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      hidden
                      onChange={(event) => upload(event.target.files)}
                    />
                  </label>
                </li>
              )}
            </ul>
            <button type="button" className="btn btn--primary btn--lg btn--block" onClick={send} disabled={busy}>
              {t("send")}
            </button>
            <p className="muted small">{t("sendHint", { days })}</p>
          </>
        )}
      </aside>
    </div>
  );
}

function AttributeField({
  field,
  value,
  onChange,
}: {
  field: AttributeDef;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (field.type === "bool") {
    return (
      <label className="check">
        <input type="checkbox" checked={value === true} onChange={(e) => onChange(e.target.checked)} />
        <span>{field.label}</span>
      </label>
    );
  }
  if (field.type === "multi_enum") {
    const chosen = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="field">
        <span>{field.label}</span>
        <div className="chips-row">
          {field.options.map((option) => {
            const on = chosen.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                className={on ? "chip chip--on" : "chip"}
                onClick={() =>
                  onChange(on ? chosen.filter((v) => v !== option.value) : [...chosen, option.value])
                }
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    );
  }
  return (
    <label className="field">
      <span>{field.label}</span>
      <select value={typeof value === "string" ? value : ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">—</option>
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
