import Link from "next/link";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";
import { SITE_URL } from "@/lib/seo";
import type { LinkChannel, TrackedLink } from "@/lib/types";

import { closeLink, saveLink } from "../../links-actions";
import { ConfirmButton } from "./ConfirmButton";
import { CopyButton } from "./CopyButton";

const CHANNELS: LinkChannel[] = ["blogger", "instagram", "tiktok", "facebook", "telegram", "youtube", "google", "partner", "other"];
const ERRORS = ["link_code_taken", "link_code_fixed", "link_code_format", "link_bad_target", "link_closed"] as const;

type Props = { searchParams: Promise<{ tab?: string; error?: string; ok?: string; code?: string }> };

/** Ad links for bloggers and channels: clicks, visitors, applications and the price of one application.
 * A finished campaign is closed and moves to the history tab with its numbers. */
export default async function LinksPage({ searchParams }: Props) {
  const { tab, error, ok, code } = await searchParams;
  const history = tab === "history";
  const all = await adminFetch<TrackedLink[]>("/admin/links");
  const active = all.filter((l) => l.is_active);
  const closed = all.filter((l) => !l.is_active).sort((a, b) => (b.closed_at ?? "").localeCompare(a.closed_at ?? ""));
  const links = history ? closed : active;

  const t = await adminT("links");
  const tc = await adminT("common");
  const locale = await getAdminLocale();
  const n = new Intl.NumberFormat(locale);
  const euro = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
  const dateTime = new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Madrid" });
  const day = new Intl.DateTimeFormat(locale, { dateStyle: "short", timeZone: "Europe/Madrid" });
  const pct = (part: number, whole: number) =>
    whole ? `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format((part / whole) * 100)}%` : "—";
  const errors = (error ?? "")
    .split(",")
    .filter(Boolean)
    .map((e) => (ERRORS.find((k) => k === e) ? t(`error.${e as (typeof ERRORS)[number]}`) : t("error.generic")));
  const base = SITE_URL.replace(/\/$/, "");
  const notice =
    ok === "created" ? t("created", { url: `${base}/go/${code ?? ""}` }) : ok === "closed" ? t("closedNotice") : ok ? tc("saved") : null;

  const fields = (link?: TrackedLink) => (
    <>
      <div className="field-row">
        <label className="field">
          <span>{t("form.name")}</span>
          <input name="name" required minLength={2} maxLength={200} defaultValue={link?.name} placeholder={t("form.namePlaceholder")} />
          {!link && <small className="muted">{t("form.nameHint", { base })}</small>}
        </label>
        <label className="field">
          <span>{t("form.channel")}</span>
          <select name="channel" defaultValue={link?.channel ?? "blogger"}>
            {CHANNELS.map((c) => (
              <option key={c} value={c}>
                {t(`channel.${c}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="field-row">
        <label className="field">
          <span>{t("form.target")}</span>
          <input name="target_path" required maxLength={300} defaultValue={link?.target_path ?? "/ua"} placeholder="/ua/robota" />
          <small className="muted">{t("form.targetHint")}</small>
        </label>
        <label className="field">
          <span>{t("form.cost")}</span>
          <input name="cost" inputMode="decimal" defaultValue={link?.cost ?? ""} placeholder="150" />
          <small className="muted">{t("form.costHint")}</small>
        </label>
      </div>
      <label className="field">
        <span>{t("form.notes")}</span>
        <input name="notes" maxLength={2000} defaultValue={link?.notes ?? ""} placeholder={t("form.notesPlaceholder")} />
      </label>
    </>
  );

  const numbers = (l: TrackedLink) => (
    <>
      <td className="num">{n.format(l.clicks)}</td>
      <td className="num">{n.format(l.visitors)}</td>
      <td className="num">
        <strong>{n.format(l.applications)}</strong>
      </td>
      <td className="num">{pct(l.applications, l.visitors)}</td>
      <td className="num">{l.cost ? euro.format(Number(l.cost)) : "—"}</td>
      <td className="num">{l.cost && l.applications ? euro.format(Number(l.cost) / l.applications) : "—"}</td>
    </>
  );

  return (
    <>
      <h1>{t("title")}</h1>
      <p className="muted">{t("intro")}</p>
      {errors.length > 0 && (
        <div className="notice notice--error">
          {errors.map((e) => (
            <div key={e}>{e}</div>
          ))}
        </div>
      )}
      {notice && <p className="notice notice--ok">{notice}</p>}

      <div className="admin-presets">
        <Link href="/admin/links" className={history ? "pill" : "pill pill--active"}>
          {t("tabActive", { count: active.length })}
        </Link>
        <Link href="/admin/links?tab=history" className={history ? "pill pill--active" : "pill"}>
          {t("tabHistory", { count: closed.length })}
        </Link>
      </div>

      {!history && (
        <details className="panel link-new" open={active.length === 0}>
          <summary>{t("new")}</summary>
          <form action={saveLink} className="link-form">
            {fields()}
            <div>
              <button type="submit" className="btn btn--primary">
                {t("form.create")}
              </button>
            </div>
          </form>
        </details>
      )}

      {links.length === 0 ? (
        <p className="muted">{history ? t("historyEmpty") : t("empty")}</p>
      ) : (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("col.link")}</th>
                <th className="num">{t("col.clicks")}</th>
                <th className="num">{t("col.visitors")}</th>
                <th className="num">{t("col.applications")}</th>
                <th className="num">{t("col.conversion")}</th>
                <th className="num">{t("col.cost")}</th>
                <th className="num">{t("col.perApplication")}</th>
                {!history && <th />}
              </tr>
            </thead>
            <tbody>
              {links.map((l) => {
                const url = `${base}/go/${l.code}`;
                return (
                  <tr key={l.id}>
                    <td>
                      <strong>{l.name}</strong> <span className="badge badge--muted">{t(`channel.${l.channel}`)}</span>
                      {history ? (
                        <div className="muted small">
                          /go/{l.code} → {l.target_path} ·{" "}
                          {t("period", { from: day.format(new Date(l.created_at)), to: day.format(new Date(l.closed_at ?? l.created_at)) })}
                        </div>
                      ) : (
                        <>
                          <div className="link-url">
                            <code>{url}</code>
                            <CopyButton text={url} label={t("copy")} done={t("copied")} />
                          </div>
                          <div className="muted small">
                            → {l.target_path}
                            {l.last_click_at && <> · {t("lastClick", { date: dateTime.format(new Date(l.last_click_at)) })}</>}
                          </div>
                        </>
                      )}
                      {l.notes && <div className="small">{l.notes}</div>}
                      {!history && (
                        <details className="link-edit">
                          <summary className="small">{t("edit")}</summary>
                          <form action={saveLink} className="link-form">
                            <input type="hidden" name="id" value={l.id} />
                            <input type="hidden" name="code" value={l.code} />
                            {fields(l)}
                            <div>
                              <button type="submit" className="btn btn--primary btn--sm">
                                {tc("save")}
                              </button>
                            </div>
                          </form>
                        </details>
                      )}
                    </td>
                    {numbers(l)}
                    {!history && (
                      <td>
                        <form action={closeLink}>
                          <input type="hidden" name="id" value={l.id} />
                          <ConfirmButton question={t("closeConfirm", { name: l.name })} className="btn btn--ghost-dark btn--sm">
                            {t("close")}
                          </ConfirmButton>
                        </form>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
