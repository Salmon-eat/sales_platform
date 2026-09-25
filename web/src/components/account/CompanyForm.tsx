"use client";

import { Building2, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { actOnCompany, deleteCompany, saveCompany } from "@/app/[locale]/company-actions";
import { asLocale } from "@/i18n/routing";
import { companyPath } from "@/lib/routes";
import type { CategoryNode, LocationRef, MyCompany, Taxonomy } from "@/lib/types";

type Props = {
  initial: MyCompany | null;
  cities: (LocationRef & { id: number })[];
  taxonomy: Taxonomy;
};

const MAX_CATEGORIES = 8;

/** Leaf categories across the board: a firm says what it does, not where its ads go. */
function services(taxonomy: Taxonomy): { id: number; name: string }[] {
  const out: { id: number; name: string }[] = [];
  const walk = (nodes: CategoryNode[], section: string) => {
    for (const node of nodes) {
      if (node.children?.length) walk(node.children, section);
      else out.push({ id: node.id, name: `${section} · ${node.name}` });
    }
  };
  for (const section of taxonomy.sections) {
    if (section.kind === "listings") walk(section.categories, section.name);
  }
  return out;
}

/** The firm's own page: written here, checked by the team, then it appears in the directory. */
export function CompanyForm({ initial, cities, taxonomy }: Props) {
  const t = useTranslations("myCompany");
  const locale = asLocale(useLocale());
  const [company, setCompany] = useState<MyCompany | null>(initial);
  const [chosen, setChosen] = useState<number[]>(initial?.category_ids ?? []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const options = services(taxonomy);

  function toggle(id: number) {
    setChosen((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : current.length < MAX_CATEGORIES
          ? [...current, id]
          : current,
    );
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (key: string) => String(form.get(key) ?? "").trim() || null;
    setBusy(true);
    setError(null);
    const result = await saveCompany(
      {
        name: String(form.get("name") ?? "").trim(),
        lang: locale,
        about: String(form.get("about") ?? "").trim(),
        city_id: form.get("city_id") ? Number(form.get("city_id")) : null,
        address: text("address"),
        hours: text("hours"),
        category_ids: chosen,
        phone: text("phone"),
        whatsapp: text("whatsapp"),
        telegram: text("telegram"),
        email: text("email"),
        site: text("site"),
      },
      locale,
    );
    setBusy(false);
    if (result.ok) {
      setCompany(result.company);
      setSaved(true);
    } else {
      setError(result.error);
    }
  }

  async function act(action: "submit" | "hide" | "reopen") {
    setBusy(true);
    const result = await actOnCompany(action, locale);
    setBusy(false);
    if (result.ok) setCompany(result.company);
    else setError(result.error);
  }

  async function upload(file: File | undefined) {
    if (!file || !company) return;
    setBusy(true);
    const response = await fetch("/api/my/company/logo", { method: "POST", body: file });
    const body = await response.json().catch(() => null);
    setBusy(false);
    if (response.ok && body) setCompany(body as MyCompany);
    else setError(body?.detail ?? "logo_failed");
  }

  async function removeAll() {
    if (!window.confirm(t("deleteConfirm"))) return;
    setBusy(true);
    await deleteCompany();
    setBusy(false);
    setCompany(null);
    setChosen([]);
  }

  return (
    <section className="company-form">
      <div className="home-block__head">
        <h2>{t("title")}</h2>
        {company && (
          <span className={`badge badge--${company.status}`}>
            {t(`status_${company.status}` as "status_draft")}
          </span>
        )}
      </div>
      <p className="muted small">{t("intro")}</p>

      {company?.status === "rejected" && company.reject_note && (
        <p className="my-ad__rejected">
          <strong>{t("rejected")}:</strong> {company.reject_note}
        </p>
      )}

      <form className="resume__form" onSubmit={submit}>
        <div className="field-row">
          <label className="field">
            <span>{t("name")}</span>
            <input name="name" required minLength={2} maxLength={120} defaultValue={company?.name ?? ""} placeholder={t("namePlaceholder")} />
          </label>
          <label className="field">
            <span>{t("city")}</span>
            <select name="city_id" defaultValue={company?.city_id ?? ""}>
              <option value="">—</option>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>
                  {city.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="field">
          <span>{t("about")}</span>
          <textarea name="about" rows={4} maxLength={4000} defaultValue={company?.about ?? ""} placeholder={t("aboutPlaceholder")} />
        </label>

        <div className="field-row">
          <label className="field">
            <span>{t("address")}</span>
            <input name="address" maxLength={200} defaultValue={company?.address ?? ""} />
          </label>
          <label className="field">
            <span>{t("hours")}</span>
            <input name="hours" maxLength={200} defaultValue={company?.hours ?? ""} placeholder={t("hoursPlaceholder")} />
          </label>
        </div>

        <div className="field">
          <span>{t("services", { max: MAX_CATEGORIES })}</span>
          <select
            className="company-form__services"
            multiple
            size={8}
            value={chosen.map(String)}
            onChange={(event) =>
              setChosen(
                Array.from(event.target.selectedOptions)
                  .slice(0, MAX_CATEGORIES)
                  .map((option) => Number(option.value)),
              )
            }
          >
            {options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </div>

        <div className="field-row">
          <label className="field">
            <span>{t("phone")}</span>
            <input name="phone" type="tel" defaultValue={company?.phone ?? ""} placeholder="+34 600 000 000" />
          </label>
          <label className="field">
            <span>WhatsApp</span>
            <input name="whatsapp" type="tel" defaultValue={company?.whatsapp ?? ""} />
          </label>
          <label className="field">
            <span>Telegram</span>
            <input name="telegram" defaultValue={company?.telegram ?? ""} placeholder="@firma" />
          </label>
        </div>
        <div className="field-row">
          <label className="field">
            <span>{t("email")}</span>
            <input name="email" type="email" defaultValue={company?.email ?? ""} />
          </label>
          <label className="field">
            <span>{t("site")}</span>
            <input name="site" defaultValue={company?.site ?? ""} placeholder="example.com" />
          </label>
        </div>

        <div className="resume__actions">
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {company ? t("save") : t("create")}
          </button>
          {saved && <span className="muted small">{t("saved")}</span>}
          {company && (
            <button type="button" className="link-button link-button--danger" onClick={removeAll}>
              {t("delete")}
            </button>
          )}
        </div>
      </form>

      {company && (
        <div className="company-form__side">
          <div className="company-form__logo">
            {company.logo ? <img src={company.logo} alt="" /> : <Building2 size={26} aria-hidden />}
            <label className="btn btn--outline btn--sm">
              {t("logo")}
              <input type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => upload(e.target.files?.[0])} />
            </label>
          </div>
          <div className="resume__actions">
            {(company.status === "draft" || company.status === "rejected" || company.status === "hidden") && (
              <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => act("submit")}>
                {t("send")}
              </button>
            )}
            {company.status === "active" && (
              <>
                <Link href={companyPath(locale, company.slug)} className="btn btn--outline btn--sm">
                  <ExternalLink size={14} aria-hidden /> {t("view")}
                </Link>
                <button type="button" className="link-button" disabled={busy} onClick={() => act("hide")}>
                  {t("hide")}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {error && (
        <p className="form-error" role="alert">
          {t.has(`errors.${error}` as "errors.generic") ? t(`errors.${error}` as "errors.generic") : t("errors.generic")}
        </p>
      )}
    </section>
  );
}
