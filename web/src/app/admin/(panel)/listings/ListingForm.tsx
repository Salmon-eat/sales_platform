"use client";

import { Languages } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState, useTransition } from "react";

import { formatEuro, formatSalaryRange, MONTHLY_FACTOR } from "@/lib/listing-format";
import type {
  AdminAttribute,
  AdminCategory,
  AdminListingDetail,
  AdminSection,
  Lang,
  ListingQuestionSetting,
  LocationBrief,
  QuestionPreset,
  SalaryPeriod,
} from "@/lib/types";

import { saveListing } from "../../listing-actions";
import { CategoryPicker } from "./CategoryPicker";
import { LocationPicker } from "./LocationPicker";
import { QuestionsFieldset } from "./QuestionsFieldset";

type Text = { title: string; description: string; requirements: string; conditions: string };
const LANGS: Lang[] = ["es", "en", "uk", "ru"];
const PERIODS: SalaryPeriod[] = ["hour", "day", "week", "month"];
const SCHEDULES = ["full", "part", "weekends", "shifts"] as const;
const CONTRACTS = ["indefinido", "temporal", "fijo_discontinuo"] as const;
const SOURCES = ["agency", "partner", "employer"] as const;
const langCode = (lang: Lang) => (lang === "uk" ? "UA" : lang.toUpperCase());
const EMPTY_TEXT: Text = { title: "", description: "", requirements: "", conditions: "" };

type Props = {
  sections: AdminSection[];
  /** ready-made questions to the candidate, in the admin language */
  presets: QuestionPreset[];
  listing?: AdminListingDetail;
  readOnly?: boolean;
};

function initialTexts(listing?: AdminListingDetail): Record<Lang, Text> {
  const texts = Object.fromEntries(LANGS.map((l) => [l, { ...EMPTY_TEXT }])) as Record<Lang, Text>;
  for (const t of listing?.translations ?? []) {
    texts[t.lang] = {
      title: t.title,
      description: t.description,
      requirements: t.requirements ?? "",
      conditions: t.conditions ?? "",
    };
  }
  return texts;
}

const isFilled = (t: Text) => Boolean(t.title.trim() || t.description.trim());
const toInt = (v: string) => (v.trim() === "" ? null : Math.round(Number(v)));

export function ListingForm({ sections, presets, listing, readOnly = false }: Props) {
  const t = useTranslations("admin.listings");
  const tc = useTranslations("admin.common");
  const locale = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [errors, setErrors] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);

  const [categoryId, setCategoryId] = useState<number | null>(listing?.category_id ?? null);
  const [scope, setScope] = useState<"local" | "spain_wide">(listing?.location_scope ?? "local");
  const [location, setLocation] = useState<LocationBrief | null>(listing?.location ?? null);
  const [tab, setTab] = useState<Lang>(listing?.original_lang ?? locale);
  const [texts, setTexts] = useState(() => initialTexts(listing));
  const [salaryMin, setSalaryMin] = useState(listing?.salary_min?.toString() ?? "");
  const [salaryMax, setSalaryMax] = useState(listing?.salary_max?.toString() ?? "");
  const [period, setPeriod] = useState<SalaryPeriod | "">(listing?.salary_period ?? "month");
  const [flags, setFlags] = useState({
    housing: listing?.housing ?? false,
    no_language: listing?.no_language ?? false,
    no_experience: listing?.no_experience ?? false,
    is_pinned: listing?.is_pinned ?? false,
  });
  const [schedule, setSchedule] = useState<string[]>(listing?.schedule ?? []);
  const [contract, setContract] = useState(listing?.contract ?? "");
  const [hiring, setHiring] = useState({
    vacancies: listing?.vacancies?.toString() ?? "",
    start_date: listing?.start_date ?? "",
    is_urgent: listing?.is_urgent ?? false,
    duration_months: listing?.duration_months?.toString() ?? "",
  });
  const [attributes, setAttributes] = useState<Record<string, unknown>>(listing?.attributes ?? {});
  const [questions, setQuestions] = useState<ListingQuestionSetting[]>(listing?.questions ?? []);
  const [source, setSource] = useState(listing?.source ?? "agency");
  const [employer, setEmployer] = useState(listing?.employer_name ?? "");
  const [contact, setContact] = useState({
    name: listing?.contact.name ?? "",
    phone: listing?.contact.phone ?? "",
    whatsapp: listing?.contact.whatsapp ?? "",
    telegram: listing?.contact.telegram ?? "",
    email: listing?.contact.email ?? "",
  });

  // category -> its sector, its section and the effective attributes (own + inherited)
  const { byId, parentOf, sectionOf } = useMemo(() => {
    const byId = new Map<number, AdminCategory>();
    const parentOf = new Map<number, AdminCategory>();
    const sectionOf = new Map<number, AdminSection>();
    for (const section of sections)
      for (const sector of section.categories) {
        byId.set(sector.id, sector);
        sectionOf.set(sector.id, section);
        for (const child of sector.children) {
          byId.set(child.id, child);
          parentOf.set(child.id, sector);
          sectionOf.set(child.id, section);
        }
      }
    return { byId, parentOf, sectionOf };
  }, [sections]);

  const category = categoryId ? byId.get(categoryId) : undefined;
  const sector = categoryId ? parentOf.get(categoryId) : undefined;
  const attributeDefs: AdminAttribute[] = [...(sector?.attributes ?? []), ...(category?.attributes ?? [])].sort(
    (a, b) => a.facet_order - b.facet_order,
  );
  // listing tags of the whole section (for students, documents, languages...): data, not code
  const sectionTags: AdminAttribute[] = [...((categoryId && sectionOf.get(categoryId)?.attributes) || [])].sort(
    (a, b) => a.facet_order - b.facet_order,
  );
  // a tag that only makes sense with another answer
  const tagHidden = (key: string) =>
    (key === "spanish_level" && flags.no_language) ||
    (key === "housing_cost" && !flags.housing) ||
    (key === "route_countries" && attributes.route_scope !== "internacional");

  const monthly =
    period && (toInt(salaryMin) ?? toInt(salaryMax)) !== null
      ? Math.round(((toInt(salaryMin) ?? toInt(salaryMax)) as number) * MONTHLY_FACTOR[period])
      : null;

  function changeCategory(id: number | null) {
    setCategoryId(id);
    // keep only attributes that still exist for the new category (section tags included)
    const next = id
      ? [
          ...(sectionOf.get(id)?.attributes ?? []),
          ...(parentOf.get(id)?.attributes ?? []),
          ...(byId.get(id)?.attributes ?? []),
        ]
      : [];
    setAttributes((prev) => Object.fromEntries(Object.entries(prev).filter(([k]) => next.some((a) => a.key === k))));
  }

  /** A starting point for a manual translation: another language's text, rewritten by the manager. */
  function copyFrom(from: Lang) {
    setTexts((prev) => ({ ...prev, [tab]: { ...prev[from] } }));
    setSaved(false);
  }

  function setText(field: keyof Text, value: string) {
    setTexts((prev) => ({ ...prev, [tab]: { ...prev[tab], [field]: value } }));
    setSaved(false);
  }

  function submit(publish: boolean) {
    const translations = LANGS.filter((l) => isFilled(texts[l])).map((lang) => ({
      lang,
      title: texts[lang].title,
      description: texts[lang].description,
      requirements: texts[lang].requirements || null,
      conditions: texts[lang].conditions || null,
    }));
    const clientErrors = [
      !categoryId && t("form.errCategory"),
      scope === "local" && !location && t("form.errLocation"),
      !LANGS.some((l) => isFilled(texts[l])) && t("form.errText"),
      // a draft can be saved any time, publishing needs the Spanish version
      publish && !isFilled(texts.es) && t("form.errPublishEs"),
    ].filter(Boolean) as string[];
    if (clientErrors.length) {
      setErrors(clientErrors);
      return;
    }

    const payload = {
      category_id: categoryId,
      location_scope: scope,
      location_id: scope === "local" ? location?.id : null,
      point: listing && location?.id === listing.location?.id ? listing.point : null,
      salary_min: toInt(salaryMin),
      salary_max: toInt(salaryMax),
      salary_period: toInt(salaryMin) !== null || toInt(salaryMax) !== null ? period || null : null,
      ...flags,
      schedule,
      contract: contract || null,
      vacancies: toInt(hiring.vacancies),
      start_date: hiring.start_date || null,
      is_urgent: hiring.is_urgent,
      duration_months: toInt(hiring.duration_months),
      // answers hidden by another answer are not sent (e.g. Spanish level for "no language")
      attributes: Object.fromEntries(Object.entries(attributes).filter(([k]) => !tagHidden(k))),
      contact: Object.fromEntries(Object.entries(contact).filter(([, v]) => v.trim())),
      questions,
      source,
      employer_name: source === "agency" ? null : employer || null,
      translations,
    };

    startTransition(async () => {
      const result = await saveListing(listing?.id ?? null, payload, publish);
      if (!result.ok) {
        setErrors(result.errors);
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
      setErrors([]);
      setSaved(true);
      if (listing) router.refresh();
      else router.push(`/admin/listings/${result.id}?created=1`);
    });
  }

  const text = texts[tab];
  const filledLangs = LANGS.filter((l) => isFilled(texts[l]));
  const previewTitle = texts[locale].title || texts[filledLangs[0] ?? locale].title || t("preview.untitled");
  const salaryText = formatSalaryRange(toInt(salaryMin), toInt(salaryMax), locale);
  const langLower = (lang: Lang) => t(`langLower.${lang}`);

  return (
    <div className="listing-editor">
      <form
        className="listing-form"
        onSubmit={(e) => {
          e.preventDefault();
          submit(false);
        }}
      >
        {errors.length > 0 && (
          <div className="notice notice--error" role="alert">
            <strong>{tc("notSaved")}</strong>
            <ul>
              {errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </div>
        )}
        {saved && <p className="notice notice--ok">{tc("saved")}</p>}

        <fieldset className="panel" disabled={readOnly}>
          <legend>{t("form.placeTitle")}</legend>
          <div className="field">
            <span>{t("form.profession")}</span>
            <CategoryPicker sections={sections} value={categoryId} onChange={changeCategory} disabled={readOnly} />
          </div>

          <div className="choice-pills">
            <button type="button" className={scope === "local" ? "pill pill--active" : "pill"} onClick={() => setScope("local")}>
              {t("form.scopeLocal")}
            </button>
            <button
              type="button"
              className={scope === "spain_wide" ? "pill pill--active" : "pill"}
              onClick={() => setScope("spain_wide")}
            >
              {t("form.scopeSpain")}
            </button>
          </div>
          {scope === "local" ? (
            <LocationPicker value={location} onChange={setLocation} disabled={readOnly} />
          ) : (
            <p className="muted small">{t("form.spainHint")}</p>
          )}
        </fieldset>

        <fieldset className="panel" disabled={readOnly}>
          <legend>{t("form.textTitle")}</legend>
          <p className="muted small">{t("form.textHint")}</p>
          <div className="lang-tabs" role="tablist">
            {LANGS.map((lang) => (
              <button
                key={lang}
                type="button"
                role="tab"
                aria-selected={tab === lang}
                className={tab === lang ? "lang-tab lang-tab--active" : "lang-tab"}
                onClick={() => setTab(lang)}
              >
                {tc(`lang_${lang}`)} · {langCode(lang)}
                {isFilled(texts[lang]) ? <span className="dot" aria-label={t("form.tabFilled")} /> : <small>{t("form.tabEmpty")}</small>}
              </button>
            ))}
          </div>

          {!isFilled(text) &&
            !readOnly &&
            filledLangs.map((from) => (
              <button key={from} type="button" className="btn btn--ghost-dark btn--sm copy-original" onClick={() => copyFrom(from)}>
                <Languages size={15} aria-hidden /> {t("form.copyFrom", { from, to: tab })}
              </button>
            ))}
          <label className="field">
            <span>{t("form.fieldTitle", { lang: langLower(tab) })}</span>
            <input value={text.title} maxLength={200} lang={tab} onChange={(e) => setText("title", e.target.value)} />
          </label>
          <label className="field">
            <span>{t("form.fieldDescription", { lang: langLower(tab) })}</span>
            <textarea rows={5} value={text.description} lang={tab} onChange={(e) => setText("description", e.target.value)} />
          </label>
          <div className="field-row">
            <label className="field">
              <span>{t("form.fieldRequirements", { lang: langLower(tab) })}</span>
              <textarea rows={3} value={text.requirements} lang={tab} onChange={(e) => setText("requirements", e.target.value)} />
            </label>
            <label className="field">
              <span>{t("form.fieldConditions", { lang: langLower(tab) })}</span>
              <textarea rows={3} value={text.conditions} lang={tab} onChange={(e) => setText("conditions", e.target.value)} />
            </label>
          </div>
        </fieldset>

        <fieldset className="panel" disabled={readOnly}>
          <legend>{t("form.salaryTitle")}</legend>
          <div className="field-row field-row--salary">
            <label className="field">
              <span>{t("form.salaryFrom")}</span>
              <input type="number" min={0} inputMode="numeric" value={salaryMin} onChange={(e) => setSalaryMin(e.target.value)} />
            </label>
            <label className="field">
              <span>{t("form.salaryTo")}</span>
              <input type="number" min={0} inputMode="numeric" value={salaryMax} onChange={(e) => setSalaryMax(e.target.value)} />
            </label>
            <label className="field">
              <span>{t("form.salaryPeriod")}</span>
              <select value={period} onChange={(e) => setPeriod(e.target.value as SalaryPeriod)}>
                {PERIODS.map((p) => (
                  <option key={p} value={p}>
                    {t(`period.${p}`)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {monthly !== null && period !== "month" && (
            <p className="muted small">{t("form.salaryMonthly", { amount: formatEuro(monthly, locale) })}</p>
          )}
          {toInt(salaryMin) === null && toInt(salaryMax) === null && (
            <p className="notice notice--warn">{t("form.salaryWarn")}</p>
          )}

          <div className="checks">
            {(
              [
                ["housing", t("form.housing")],
                ["no_language", t("form.noLanguage")],
                ["no_experience", t("form.noExperience")],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="check">
                <input type="checkbox" checked={flags[key]} onChange={(e) => setFlags({ ...flags, [key]: e.target.checked })} />
                {label}
              </label>
            ))}
          </div>

          <div className="field">
            <span>{t("form.schedule")}</span>
            <div className="choice-pills">
              {SCHEDULES.map((value) => {
                const on = schedule.includes(value);
                return (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={on}
                    className={on ? "pill pill--active" : "pill"}
                    onClick={() => setSchedule(on ? schedule.filter((s) => s !== value) : [...schedule, value])}
                  >
                    {t(`schedule.${value}`)}
                  </button>
                );
              })}
            </div>
          </div>
          <label className="field">
            <span>{t("form.contract")}</span>
            <select value={contract} onChange={(e) => setContract(e.target.value)}>
              <option value="">{tc("notSet")}</option>
              {CONTRACTS.map((value) => (
                <option key={value} value={value}>
                  {t(`contract.${value}`)}
                </option>
              ))}
            </select>
          </label>
        </fieldset>

        {sectionTags.length > 0 && (
          <fieldset className="panel" disabled={readOnly}>
            <legend>{t("form.tagsTitle")}</legend>
            <p className="muted small">{t("form.tagsHint")}</p>
            <div className="tag-fields">
              {sectionTags
                .filter((attr) => !tagHidden(attr.key))
                .map((attr) => (
                  <AttributeField
                    key={attr.id}
                    attr={attr}
                    value={attributes[attr.key]}
                    onChange={(value) => setAttributes((prev) => ({ ...prev, [attr.key]: value }))}
                  />
                ))}
            </div>
          </fieldset>
        )}

        <fieldset className="panel" disabled={readOnly}>
          <legend>{t("form.hiringTitle")}</legend>
          <div className="field-row">
            <label className="field">
              <span>{t("form.vacancies")}</span>
              <input
                type="number"
                min={1}
                max={999}
                inputMode="numeric"
                value={hiring.vacancies}
                onChange={(e) => setHiring({ ...hiring, vacancies: e.target.value })}
              />
            </label>
            <label className="field">
              <span>{t("form.startDate")}</span>
              <input type="date" value={hiring.start_date} onChange={(e) => setHiring({ ...hiring, start_date: e.target.value })} />
            </label>
            <label className="field">
              <span>{t("form.duration")}</span>
              <input
                type="number"
                min={1}
                max={36}
                inputMode="numeric"
                value={hiring.duration_months}
                onChange={(e) => setHiring({ ...hiring, duration_months: e.target.value })}
              />
            </label>
          </div>
          <label className="check">
            <input type="checkbox" checked={hiring.is_urgent} onChange={(e) => setHiring({ ...hiring, is_urgent: e.target.checked })} />
            {t("form.urgent")}
          </label>
        </fieldset>

        <QuestionsFieldset presets={presets} value={questions} onChange={setQuestions} disabled={readOnly} />

        {attributeDefs.length > 0 && (
          <fieldset className="panel" disabled={readOnly}>
            <legend>{t("form.attributesTitle", { category: category ? category.name[locale] || category.name.es : "" })}</legend>
            {attributeDefs.filter((attr) => !tagHidden(attr.key)).map((attr) => (
              <AttributeField
                key={attr.id}
                attr={attr}
                value={attributes[attr.key]}
                onChange={(value) => setAttributes((prev) => ({ ...prev, [attr.key]: value }))}
              />
            ))}
          </fieldset>
        )}

        <fieldset className="panel" disabled={readOnly}>
          <legend>{t("form.sourceTitle")}</legend>
          <div className="field-row">
            <label className="field">
              <span>{t("form.source")}</span>
              <select value={source} onChange={(e) => setSource(e.target.value as typeof source)}>
                {SOURCES.map((value) => (
                  <option key={value} value={value}>
                    {t(`source.${value}`)}
                  </option>
                ))}
              </select>
            </label>
            {source !== "agency" && (
              <label className="field">
                <span>{t("form.company")}</span>
                <input value={employer} maxLength={200} onChange={(e) => setEmployer(e.target.value)} />
              </label>
            )}
          </div>
          <div className="field-row">
            {(
              [
                ["name", t("form.contactName")],
                ["phone", t("form.contactPhone")],
                ["whatsapp", t("form.contactWhatsapp")],
                ["telegram", t("form.contactTelegram")],
                ["email", t("form.contactEmail")],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="field">
                <span>{label}</span>
                <input value={contact[key]} onChange={(e) => setContact({ ...contact, [key]: e.target.value })} />
              </label>
            ))}
          </div>
          <label className="check">
            <input type="checkbox" checked={flags.is_pinned} onChange={(e) => setFlags({ ...flags, is_pinned: e.target.checked })} />
            {t("form.pinned")}
          </label>
        </fieldset>

        {!readOnly && (
          <div className="form-actions">
            <button type="submit" className="btn btn--ghost-dark btn--lg" disabled={pending}>
              {pending ? t("form.saving") : listing ? tc("save") : t("form.saveDraft")}
            </button>
            {(!listing || listing.status === "draft") && (
              <button type="button" className="btn btn--primary btn--lg" disabled={pending} onClick={() => submit(true)}>
                {t("form.saveAndPublish")}
              </button>
            )}
          </div>
        )}
      </form>

      <aside className="listing-preview">
        <span className="muted small">{t("preview.caption")}</span>
        <article className="job-card">
          <div className="job-card-salary">
            {salaryText ? (
              <>
                <strong>{salaryText}</strong>
                <small>{t("preview.perPeriod", { period: period || "month" })}</small>
              </>
            ) : (
              <span className="job-card-nosalary">{t("preview.noSalary")}</span>
            )}
          </div>
          <div className="job-card-main">
            <h3>
              {previewTitle}
              {hiring.is_urgent && <span className="urgent-badge">{t("preview.urgent")}</span>}
            </h3>
            <p className="job-card-meta">
              {[
                source === "agency" ? t("preview.agency") : employer || t("preview.company"),
                scope === "spain_wide" ? t("preview.spainWide") : (location?.name ?? t("preview.city")),
                t("preview.justNow"),
              ].join(" · ")}
            </p>
          </div>
          <div className="job-card-foot">
            <ul className="job-tags">
              {[
                flags.housing && t("preview.tagHousing"),
                flags.no_language && t("preview.tagNoLanguage"),
                flags.no_experience && t("preview.tagNoExperience"),
              ]
                .filter(Boolean)
                .map((tag, i) => (
                  <li key={String(tag)} className={i === 0 && flags.housing ? "job-tag job-tag--ok" : "job-tag"}>
                    {tag}
                  </li>
                ))}
            </ul>
            <span className="btn btn--primary btn--sm">{t("preview.apply")}</span>
          </div>
        </article>
        <p className="muted small">
          {t("preview.langs")} {LANGS.map((l) => `${langCode(l)} ${isFilled(texts[l]) ? "✓" : "—"}`).join("  ")}
          {!isFilled(texts.es) && ` · ${t("preview.needsEs")}`}
        </p>
        {listing?.translations.map((tr) => (
          <p key={tr.lang} className="muted small slug-line">
            {langCode(tr.lang)}: <code>/oferta/{tr.slug}-{listing.id}</code>
          </p>
        ))}
      </aside>
    </div>
  );
}

function AttributeField({
  attr,
  value,
  onChange,
}: {
  attr: AdminAttribute;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const t = useTranslations("admin.listings");
  const tc = useTranslations("admin.common");
  const locale = useLocale();
  const label = `${attr.label[locale] || attr.label.es}${attr.required ? " *" : ""}`;

  if (attr.type === "bool") {
    return (
      <label className="check">
        <input type="checkbox" checked={value === true} onChange={(e) => onChange(e.target.checked)} />
        {label}
      </label>
    );
  }
  if (attr.type === "enum") {
    return (
      <label className="field">
        <span>{label}</span>
        <select value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">{tc("notSet")}</option>
          {attr.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label[locale] || o.label.es}
            </option>
          ))}
        </select>
      </label>
    );
  }
  if (attr.type === "multi_enum") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="field">
        <span>{label}</span>
        <div className="choice-pills">
          {attr.options.map((o) => {
            const on = selected.includes(o.value);
            return (
              <button
                key={o.value}
                type="button"
                aria-pressed={on}
                className={on ? "pill pill--active" : "pill"}
                onClick={() => onChange(on ? selected.filter((v) => v !== o.value) : [...selected, o.value])}
              >
                {o.label[locale] || o.label.es}
              </button>
            );
          })}
        </div>
      </div>
    );
  }
  const range = (value as { min?: number; max?: number }) ?? {};
  return (
    <div className="field">
      <span>{label}</span>
      <div className="field-row">
        {(["min", "max"] as const).map((k) => (
          <input
            key={k}
            type="number"
            placeholder={k === "min" ? t("form.rangeFrom") : t("form.rangeTo")}
            value={range[k] ?? ""}
            onChange={(e) => onChange({ ...range, [k]: e.target.value === "" ? undefined : Number(e.target.value) })}
          />
        ))}
      </div>
    </div>
  );
}
