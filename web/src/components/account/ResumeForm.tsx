"use client";

import { FileText, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useRef, useState } from "react";

import { deleteResume, deleteResumeFile, saveResume } from "@/app/[locale]/resume-actions";
import { asLocale } from "@/i18n/routing";
import type { LanguageLevel, Licence, LocationRef, Resume } from "@/lib/types";

const LICENCES: Licence[] = ["b", "c", "ce", "d", "code95", "adr", "forklift", "crane"];
const LEVELS: LanguageLevel[] = ["a1", "a2", "b1", "b2", "c1", "native"];
const LANGS = ["es", "en", "uk", "ru"] as const;
const SCHEDULES = ["full", "part", "shifts", "weekends"] as const;

type Props = { initial: Resume | null; cities: (LocationRef & { id: number })[] };

/** The CV people keep in their account: filled in once, sent with one press afterwards. */
export function ResumeForm({ initial, cities }: Props) {
  const t = useTranslations("resume");
  const ts = useTranslations("search");
  const locale = asLocale(useLocale());
  const [resume, setResume] = useState<Resume | null>(initial);
  const [licences, setLicences] = useState<Licence[]>(initial?.licences ?? []);
  const [languages, setLanguages] = useState<Partial<Record<string, LanguageLevel>>>(
    initial?.languages ?? {},
  );
  const [schedule, setSchedule] = useState<string[]>(initial?.schedule ?? []);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  function toggle<T extends string>(list: T[], value: T, set: (next: T[]) => void) {
    set(list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const number = (key: string) => {
      const raw = String(form.get(key) ?? "").trim();
      return raw ? Number(raw) : null;
    };
    setBusy(true);
    setError(null);
    const result = await saveResume(
      {
        title: String(form.get("title") ?? "").trim(),
        about: String(form.get("about") ?? "").trim(),
        city_id: number("city_id"),
        relocate: form.get("relocate") !== null,
        experience_years: number("experience_years"),
        languages,
        licences,
        has_car: form.get("has_car") !== null,
        work_permit: form.get("work_permit") !== null,
        schedule,
        salary_min: number("salary_min"),
        salary_period: "month",
        is_public: form.get("is_public") !== null,
      },
      locale,
    );
    setBusy(false);
    if (result.ok) {
      setResume(result.resume);
      setSaved(true);
    } else {
      setError(result.error);
    }
  }

  async function upload(file: File | undefined) {
    if (!file || !resume) return;
    setBusy(true);
    setError(null);
    const response = await fetch("/api/my/resume/file", {
      method: "POST",
      headers: { "X-File-Name": encodeURIComponent(file.name) },
      body: file,
    });
    const body = await response.json().catch(() => null);
    setBusy(false);
    if (response.ok && body) setResume(body as Resume);
    else setError(body?.detail ?? body?.error ?? "file_failed");
    if (fileInput.current) fileInput.current.value = "";
  }

  async function removeFile() {
    setBusy(true);
    const result = await deleteResumeFile(locale);
    setBusy(false);
    if (result.ok) setResume(result.resume);
  }

  async function removeAll() {
    if (!window.confirm(t("deleteConfirm"))) return;
    setBusy(true);
    await deleteResume();
    setBusy(false);
    setResume(null);
    setLicences([]);
    setLanguages({});
    setSchedule([]);
  }

  return (
    <section className="resume">
      <div className="home-block__head">
        <h2>{t("title")}</h2>
        {resume && <span className="muted small">{t("savedNote")}</span>}
      </div>

      <form className="resume__form" onSubmit={submit}>
        <label className="field">
          <span>{t("headline")}</span>
          <input
            name="title"
            required
            minLength={3}
            maxLength={120}
            defaultValue={resume?.title ?? ""}
            placeholder={t("headlinePlaceholder")}
          />
        </label>

        <label className="field">
          <span>{t("about")}</span>
          <textarea
            name="about"
            rows={4}
            maxLength={3000}
            defaultValue={resume?.about ?? ""}
            placeholder={t("aboutPlaceholder")}
          />
        </label>

        <div className="field-row">
          <label className="field">
            <span>{t("city")}</span>
            <select name="city_id" defaultValue={resume?.city_id ?? ""}>
              <option value="">{ts("allPlaces")}</option>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>
                  {city.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("experience")}</span>
            <input
              name="experience_years"
              type="number"
              min={0}
              max={60}
              defaultValue={resume?.experience_years ?? ""}
              placeholder="0"
            />
          </label>
          <label className="field">
            <span>{t("salary")}</span>
            <input
              name="salary_min"
              type="number"
              min={0}
              step={50}
              defaultValue={resume?.salary_min ?? ""}
              placeholder="€ / міс"
            />
          </label>
        </div>

        <div className="field">
          <span>{t("licences")}</span>
          <div className="chips-row">
            {LICENCES.map((licence) => (
              <button
                key={licence}
                type="button"
                className={licences.includes(licence) ? "chip chip--on" : "chip"}
                onClick={() => toggle(licences, licence, setLicences)}
              >
                {t(`licence_${licence}` as "licence_b")}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <span>{t("languages")}</span>
          <div className="resume__langs">
            {LANGS.map((code) => (
              <label key={code} className="resume__lang">
                <span>{t(`lang_${code}` as "lang_es")}</span>
                <select
                  value={languages[code] ?? ""}
                  onChange={(event) =>
                    setLanguages((current) => {
                      const next = { ...current };
                      if (event.target.value) next[code] = event.target.value as LanguageLevel;
                      else delete next[code];
                      return next;
                    })
                  }
                >
                  <option value="">—</option>
                  {LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {t(`level_${level}` as "level_a1")}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        </div>

        <div className="field">
          <span>{t("schedule")}</span>
          <div className="chips-row">
            {SCHEDULES.map((item) => (
              <button
                key={item}
                type="button"
                className={schedule.includes(item) ? "chip chip--on" : "chip"}
                onClick={() => toggle(schedule, item, setSchedule)}
              >
                {ts(`schedule_${item}` as "schedule_full")}
              </button>
            ))}
          </div>
        </div>

        <div className="resume__checks">
          <label className="check">
            <input type="checkbox" name="work_permit" defaultChecked={resume?.work_permit ?? false} />
            <span>{t("workPermit")}</span>
          </label>
          <label className="check">
            <input type="checkbox" name="has_car" defaultChecked={resume?.has_car ?? false} />
            <span>{t("hasCar")}</span>
          </label>
          <label className="check">
            <input type="checkbox" name="relocate" defaultChecked={resume?.relocate ?? false} />
            <span>{t("relocate")}</span>
          </label>
          <label className="check">
            <input type="checkbox" name="is_public" defaultChecked={resume?.is_public ?? true} />
            <span>{t("isPublic")}</span>
          </label>
        </div>

        <div className="resume__actions">
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {resume ? t("saveChanges") : t("create")}
          </button>
          {saved && <span className="muted small">{t("saved")}</span>}
          {resume && (
            <button type="button" className="link-button link-button--danger" onClick={removeAll}>
              {t("delete")}
            </button>
          )}
        </div>
      </form>

      {resume && (
        <div className="resume__file">
          <h3>{t("fileTitle")}</h3>
          {resume.file_name ? (
            <p className="resume__file-row">
              <FileText size={16} aria-hidden /> {resume.file_name}
              <button type="button" className="link-button" onClick={removeFile} disabled={busy}>
                <Trash2 size={14} aria-hidden /> {t("fileRemove")}
              </button>
            </p>
          ) : (
            <p className="muted small">{t("fileNone")}</p>
          )}
          <label className="btn btn--outline btn--sm">
            {t("fileAdd")}
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.doc,.docx,image/jpeg,image/png"
              hidden
              onChange={(event) => upload(event.target.files?.[0])}
            />
          </label>
          <p className="muted small">{t("fileHint")}</p>
        </div>
      )}

      {error && (
        <p className="form-error" role="alert">
          {t.has(`errors.${error}` as "errors.generic")
            ? t(`errors.${error}` as "errors.generic")
            : t("errors.generic")}
        </p>
      )}
    </section>
  );
}
