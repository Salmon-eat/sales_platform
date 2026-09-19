import { Pin, Plus } from "lucide-react";
import Link from "next/link";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";
import { formatSalaryRange } from "@/lib/listing-format";
import type { AdminListingItem, ListingStatus, Page } from "@/lib/types";

import { runListingAction } from "../../listing-actions";

type Search = { status?: string; q?: string; mine?: string; page?: string; error?: string };
type Props = { searchParams: Promise<Search> };

const FILTER_STATUSES: ListingStatus[] = ["active", "draft", "paused", "expired", "closed"];

function href(params: Search) {
  const qs = new URLSearchParams(Object.entries(params).filter(([k, v]) => v && k !== "error") as [string, string][]);
  return `/admin/listings${qs.size ? `?${qs}` : ""}`;
}

export default async function ListingsPage({ searchParams }: Props) {
  const params = await searchParams;
  const t = await adminT("listings");
  const tc = await adminT("common");
  const locale = await getAdminLocale();
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "short", timeZone: "Europe/Madrid" });

  const query = new URLSearchParams({ page: params.page ?? "1", per_page: "30" });
  if (params.status) query.set("status", params.status);
  if (params.q) query.set("q", params.q);
  if (params.mine) query.set("mine", "true");
  const data = await adminFetch<Page<AdminListingItem>>(`/admin/listings?${query}`);
  const page = data.page;

  return (
    <>
      <div className="admin-head">
        <h1>{t("list.title")}</h1>
        <Link href="/admin/listings/new" className="btn btn--primary">
          <Plus size={16} aria-hidden /> {t("list.new")}
        </Link>
      </div>
      {params.error && <p className="notice notice--error">{params.error}</p>}

      <div className="admin-presets">
        <Link href={href({ ...params, status: undefined, page: undefined })} className={!params.status ? "pill pill--active" : "pill"}>
          {tc("all")}
        </Link>
        {FILTER_STATUSES.map((s) => (
          <Link key={s} href={href({ ...params, status: s, page: undefined })} className={params.status === s ? "pill pill--active" : "pill"}>
            {t(`status.${s}`)}
          </Link>
        ))}
        <Link
          href={href({ ...params, mine: params.mine ? undefined : "1", page: undefined })}
          className={params.mine ? "pill pill--active" : "pill"}
        >
          {t("list.mine")}
        </Link>
      </div>

      <form className="admin-filters" action="/admin/listings">
        {params.status && <input type="hidden" name="status" value={params.status} />}
        {params.mine && <input type="hidden" name="mine" value="1" />}
        <input name="q" defaultValue={params.q} placeholder={t("list.searchPlaceholder")} />
        <button type="submit" className="btn btn--primary">
          {tc("find")}
        </button>
      </form>

      <p className="muted small">{tc("found", { count: data.total })}</p>

      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("list.colListing")}</th>
              <th>{t("list.colCategory")}</th>
              <th>{t("list.colCity")}</th>
              <th>{t("list.colSalary")}</th>
              <th>{t("list.colStatus")}</th>
              <th>{t("list.colUntil")}</th>
              <th>{t("list.colAuthor")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.items.map((l) => (
              <tr key={l.id}>
                <td>
                  <Link href={`/admin/listings/${l.id}`} className="table-title">
                    {l.is_pinned && <Pin size={13} aria-label={t("list.pinned")} />} {l.title}
                  </Link>
                  <div className="lang-chips">
                    <span className="muted small">№{l.id}</span>
                    {l.langs.map((lang) => (
                      <span key={lang} className={lang === l.original_lang ? "lang-chip lang-chip--original" : "lang-chip"}>
                        {lang === "uk" ? "UA" : lang.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="small">
                  {l.sector_name && <span className="muted">{l.sector_name} › </span>}
                  {l.category_name}
                </td>
                <td className="small">{l.location_scope === "spain_wide" ? t("list.spainWide") : l.location?.name}</td>
                <td className="small num">
                  {l.salary_period
                    ? `${formatSalaryRange(l.salary_min, l.salary_max, locale)}${t(`periodShort.${l.salary_period}`)}`
                    : "—"}
                </td>
                <td>
                  <span className={`status status--${l.status}`}>{t(`status.${l.status}`)}</span>
                </td>
                <td className="small">{l.expires_at ? date.format(new Date(l.expires_at)) : "—"}</td>
                <td className="small muted">{l.created_by_email ?? "—"}</td>
                <td>
                  <form action={runListingAction} className="inline-form">
                    <input type="hidden" name="id" value={l.id} />
                    <input type="hidden" name="back" value={href(params)} />
                    {l.can_edit && l.status === "draft" && (
                      <button name="action" value="publish" className="btn btn--primary btn--sm">
                        {t("actions.publish")}
                      </button>
                    )}
                    {l.can_edit && l.status === "expired" && (
                      <button name="action" value="extend" className="btn btn--primary btn--sm">
                        {t("actions.extendShort")}
                      </button>
                    )}
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.pages > 1 && (
        <nav className="admin-pagination">
          {page > 1 ? <Link href={href({ ...params, page: String(page - 1) })}>{tc("prev")}</Link> : <span />}
          <span className="muted">{tc("pageOf", { page, pages: data.pages })}</span>
          {page < data.pages ? <Link href={href({ ...params, page: String(page + 1) })}>{tc("next")}</Link> : <span />}
        </nav>
      )}
    </>
  );
}
