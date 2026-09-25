import { Flag, UserX } from "lucide-react";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";

import { resolveReport } from "../../reports-actions";

type Report = {
  id: number;
  reason: string;
  note: string | null;
  created_at: string;
  also_reported: number;
  listing_id: number;
  listing_title: string;
  listing_text: string;
  listing_status: string;
  section_name: string;
  owner_id: number | null;
  owner_name: string | null;
  owner_active: boolean | null;
};

/** Complaints from readers. A complaint changes nothing by itself — a person decides here. */
export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; error?: string }>;
}) {
  const { ok, error } = await searchParams;
  const t = await adminT("reports");
  const locale = await getAdminLocale();
  const queue = await adminFetch<Report[]>("/admin/reports/queue");
  const when = new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });

  return (
    <section className="admin-section">
      <header className="admin-head">
        <div>
          <h1>{t("title")}</h1>
          <p className="muted">{t("subtitle")}</p>
        </div>
        <span className="admin-count">{t("waiting", { count: queue.length })}</span>
      </header>

      {ok && <p className="notice notice--ok">{t("done")}</p>}
      {error && <p className="notice notice--error">{t("failed")}</p>}

      {queue.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <ul className="mod-list">
          {queue.map((report) => (
            <li key={report.id} className="mod-card">
              <div className="mod-card__text">
                <div className="mod-card__top">
                  <span className="badge badge--rejected">
                    <Flag size={12} aria-hidden /> {t(`reason_${report.reason}` as "reason_other")}
                  </span>
                  <span className="muted small">
                    #{report.listing_id} · {report.section_name} · {when.format(new Date(report.created_at))}
                    {report.also_reported > 0 && ` · ${t("alsoReported", { count: report.also_reported })}`}
                  </span>
                </div>
                <h2>{report.listing_title}</h2>
                {report.note && <p className="mod-card__flags">{report.note}</p>}
                <p className="mod-card__body">{report.listing_text.slice(0, 600)}</p>
                <dl className="mod-card__meta">
                  <div>
                    <dt>{t("author")}</dt>
                    <dd>
                      {report.owner_name ?? "—"}
                      {report.owner_active === false && ` · ${t("blocked")}`}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("listingStatus")}</dt>
                    <dd>{report.listing_status}</dd>
                  </div>
                </dl>
              </div>

              <div className="mod-card__side">
                <form action={resolveReport}>
                  <input type="hidden" name="id" value={report.id} />
                  <input type="hidden" name="action" value="reject" />
                  <button type="submit" className="btn btn--outline btn--block">
                    {t("keep")}
                  </button>
                </form>
                <form action={resolveReport} className="mod-card__reject">
                  <input type="hidden" name="id" value={report.id} />
                  <input type="hidden" name="action" value="accept" />
                  <button type="submit" className="btn btn--primary btn--block">
                    {t("takeDown")}
                  </button>
                  <label className="field">
                    <span>
                      <UserX size={13} aria-hidden /> {t("blockToo")}
                    </span>
                    <input name="block_reason" maxLength={200} placeholder={t("blockPlaceholder")} />
                  </label>
                  <small className="muted">{t("blockHint")}</small>
                </form>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
