import Link from "next/link";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";
import type { AdminApplication, Page } from "@/lib/types";

import { StatusSelect } from "./StatusSelect";
import { STATUSES } from "./statuses";

type Props = { searchParams: Promise<{ from?: string; status?: string; stale?: string; page?: string }> };

/** Where a request without a listing came from: the site chat, the Telegram bot, else "call me". */
const KIND: Record<string, "message" | "telegram"> = { chat: "message", bot: "telegram" };
const KIND_BADGE: Record<string, string> = { chat: "badge--chat", bot: "badge--tg" };

export default async function ApplicationsPage({ searchParams }: Props) {
  const { from, status, stale, page = "1" } = await searchParams;
  // two separate tabs: the site's own applications and the Telegram bot's (a mirror of the bot)
  const fromBot = from === "bot";
  const base = fromBot ? "/admin/applications?from=bot" : "/admin/applications";
  const withBase = (params: string) => `${base}${fromBot ? "&" : "?"}${params}`;
  const query = new URLSearchParams({ page, origin: fromBot ? "bot" : "site" });
  if (status && status in STATUSES) query.set("status", status);
  if (stale === "1") query.set("stale", "true");
  const data = await adminFetch<Page<AdminApplication>>(`/admin/applications?${query}`);

  const t = await adminT("applications");
  const tc = await adminT("common");
  const dateTime = new Intl.DateTimeFormat(await getAdminLocale(), {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });
  const statuses = Object.entries(STATUSES).map(([value, key]) => [value, t(`status.${key}`)] as const);

  return (
    <>
      <h1>{t("title")}</h1>
      <nav className="admin-tabs" aria-label={t("title")}>
        <Link href="/admin/applications" className={fromBot ? "admin-tab" : "admin-tab admin-tab--active"}>
          {t("tabs.site")}
        </Link>
        <Link href="/admin/applications?from=bot" className={fromBot ? "admin-tab admin-tab--active" : "admin-tab"}>
          {t("tabs.bot")}
        </Link>
      </nav>
      <p className="muted">{t(fromBot ? "botIntro" : "intro")}</p>

      <div className="admin-presets">
        <Link href={base} className={!status && !stale ? "pill pill--active" : "pill"}>
          {tc("all")}
        </Link>
        {statuses.map(([value, label]) => (
          <Link
            key={value}
            href={withBase(`status=${value}`)}
            className={status === value && !stale ? "pill pill--active" : "pill"}
          >
            {label}
          </Link>
        ))}
        <Link href={withBase("stale=1")} className={stale === "1" ? "pill pill--active" : "pill pill--warn"}>
          {t("stale")}
        </Link>
      </div>

      {data.items.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("table.date")}</th>
                <th>{t("table.candidate")}</th>
                <th>{t("table.request")}</th>
                <th>{t("table.contact")}</th>
                <th>{t("table.inSpain")}</th>
                <th>{t("table.comment")}</th>
                <th>{t("table.status")}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id} className={a.stale ? "row--stale" : undefined}>
                  <td className="small">
                    {dateTime.format(new Date(a.created_at))}
                    {a.stale && <div className="stale-mark">{t("staleMark")}</div>}
                    <div className="muted">
                      #{a.id} · {a.lang.toUpperCase()}
                    </div>
                  </td>
                  <td>
                    <Link href={`/admin/applications/${a.id}`} className="row-link">
                      <strong>{a.name}</strong>
                    </Link>
                    {a.unread > 0 && <div className="badge badge--chat">{t("row.unread", { count: a.unread })}</div>}
                    {a.has_cv && <div className="badge badge--muted">📎 {t("row.cv")}</div>}
                    <div>{a.phone ? <a href={`tel:${a.phone}`}>{a.phone}</a> : <span className="muted small">{t("row.noPhone")}</span>}</div>
                  </td>
                  <td>
                    {a.listing ? (
                      <>
                        <div className="badge">{t("kind.response")}</div>
                        <div>
                          <Link href={`/admin/listings/${a.listing.id}`}>{a.listing.title}</Link>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className={`badge ${KIND_BADGE[a.source] ?? "badge--muted"}`}>{t(`kind.${KIND[a.source] ?? "callback"}`)}</div>
                        <div>{a.category_name ?? <span className="muted">{t("row.anyCategory")}</span>}</div>
                      </>
                    )}
                    <div className="muted small">{a.location_name ?? t("row.noCity")}</div>
                  </td>
                  <td>
                    {t(`messenger.${a.messenger}`)}
                    {a.notes_count > 0 && (
                      <div className="badge badge--muted">{t("row.repeats", { count: a.notes_count })}</div>
                    )}
                  </td>
                  <td>{a.in_spain === null ? "—" : a.in_spain ? tc("yes") : tc("no")}</td>
                  <td className="small aliases">{a.comment ?? "—"}</td>
                  <td>
                    <StatusSelect key={a.status} id={a.id} value={a.status} options={statuses} label={t("table.status")} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
