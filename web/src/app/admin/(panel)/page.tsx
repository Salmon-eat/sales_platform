import { AlertTriangle, Lightbulb, TrendingUp } from "lucide-react";
import Link from "next/link";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch, getCurrentUser } from "@/lib/auth";
import type { AdminDashboard } from "@/lib/types";

import { STATUSES } from "./applications/statuses";
import { Bars, DailyChart, Delta, Kpi, Panel } from "./dashboard-parts";

const PERIODS = [1, 7, 30, 90] as const;
const KNOWN_SOURCES = new Set([
  "direct",
  "google",
  "bing",
  "yandex",
  "duckduckgo",
  "instagram",
  "facebook",
  "telegram",
  "tiktok",
  "youtube",
  "whatsapp",
  "viber",
  "blogger",
  "partner",
  "other",
]);

type Props = { searchParams: Promise<{ days?: string }> };
type Insight = { tone: "warn" | "tip" | "good"; text: string; href?: string };

export default async function AdminDashboardPage({ searchParams }: Props) {
  const { days: raw } = await searchParams;
  const days = PERIODS.find((p) => String(p) === raw) ?? 7;
  const [d, user] = await Promise.all([adminFetch<AdminDashboard>(`/admin/dashboard?days=${days}`), getCurrentUser()]);
  const isAdmin = user?.role === "admin";

  const t = await adminT("dashboard");
  const ts = await adminT("shell");
  const ta = await adminT("applications");
  const locale = await getAdminLocale();
  const n = new Intl.NumberFormat(locale);
  const pct = (part: number, whole: number) => (whole ? Math.round((part / whole) * 1000) / 10 : 0);
  const pctText = (v: number) => `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(v)}%`;
  const euro = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
  const duration = (sec: number) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
  const ago = (iso: string) => Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 3_600_000));
  const sourceLabel = (s: string) => (KNOWN_SOURCES.has(s) ? t(`source.${s as "direct"}`) : s);

  const tr = d.traffic;
  const prev = d.traffic_prev;
  const bounceRate = pct(tr.bounces, tr.sessions);
  const conversion = pct(tr.sent, tr.sessions);
  const w = d.work;
  const mobileShare = pct(d.devices.find((x) => x.key === "mobile")?.visitors ?? 0, tr.visitors);

  // ---------- what to look at first ----------
  const insights: Insight[] = [];
  if (w.stale) insights.push({ tone: "warn", text: t("insight.stale", { count: w.stale }), href: "/admin/applications?stale=1" });
  if (w.new) insights.push({ tone: "warn", text: t("insight.new", { count: w.new }), href: "/admin/applications?status=new" });
  for (const l of d.unanswered_listings.slice(0, 3)) {
    insights.push({
      tone: "warn",
      text: t("insight.noResponses", { title: l.title ?? `№${l.id}`, views: l.views }),
      href: `/admin/listings/${l.id}`,
    });
  }
  if (tr.opened >= 10 && tr.sent / tr.opened < 0.7) {
    insights.push({ tone: "tip", text: t("insight.formDropoff", { percent: pctText(100 - pct(tr.sent, tr.opened)) }) });
  }
  if (tr.sessions >= 20 && bounceRate >= 45) {
    insights.push({ tone: "tip", text: t("insight.bounce", { percent: pctText(bounceRate) }) });
  }
  if (d.listings.active_no_salary) {
    insights.push({ tone: "tip", text: t("insight.noSalary", { count: d.listings.active_no_salary }), href: "/admin/listings?status=active" });
  }
  if (d.listings.active_no_uk) insights.push({ tone: "tip", text: t("insight.noUk", { count: d.listings.active_no_uk }), href: "/admin/listings?status=active" });
  if (d.listings.active_no_ru) insights.push({ tone: "tip", text: t("insight.noRu", { count: d.listings.active_no_ru }), href: "/admin/listings?status=active" });
  if (d.listings.expiring) insights.push({ tone: "tip", text: t("insight.expiring", { count: d.listings.expiring }), href: "/admin/listings?status=active" });
  const topMiss = d.misses[0];
  if (topMiss && topMiss.hits >= 3) {
    insights.push({ tone: "tip", text: t("insight.searchMiss", { q: topMiss.q, count: topMiss.hits }), href: "#misses" });
  }
  const bestCampaign = [...d.campaigns].filter((c) => c.applications > 0).sort((a, b) => b.applications - a.applications)[0];
  if (bestCampaign) {
    insights.push({
      tone: "good",
      text: t("insight.bestLink", { name: bestCampaign.name, count: bestCampaign.applications }),
      href: "/admin/links",
    });
  }
  const bestSource = [...d.sources].filter((s) => s.visitors >= 20).sort((a, b) => b.applications / b.visitors - a.applications / a.visitors)[0];
  if (bestSource && bestSource.applications > 0) {
    insights.push({
      tone: "good",
      text: t("insight.bestSource", { source: sourceLabel(bestSource.source), percent: pctText(pct(bestSource.applications, bestSource.visitors)) }),
    });
  }
  if (mobileShare >= 60) insights.push({ tone: "good", text: t("insight.mobile", { percent: pctText(mobileShare) }) });

  const funnel = [
    [t("funnel.visits"), tr.sessions],
    [t("funnel.viewedJob"), tr.viewed_job],
    [t("funnel.opened"), tr.opened],
    [t("funnel.sent"), tr.sent],
  ] as const;

  const listingRow = (l: AdminDashboard["top_listings"][number]) => (
    <tr key={l.id}>
      <td>
        <Link href={`/admin/listings/${l.id}`}>{l.title ?? `№${l.id}`}</Link>
        {l.no_salary && <span className="badge badge--muted">{t("listings.noSalary")}</span>}
      </td>
      <td className="num">{n.format(l.views)}</td>
      <td className="num">{n.format(l.applications)}</td>
      <td className="num">{pctText(pct(l.applications, l.views))}</td>
    </tr>
  );

  return (
    <>
      <h1>{ts("dashboard")}</h1>

      <div className="admin-presets">
        {PERIODS.map((p) => (
          <Link key={p} href={p === 7 ? "/admin" : `/admin?days=${p}`} className={p === days ? "pill pill--active" : "pill"}>
            {t(`period.d${p}`)}
          </Link>
        ))}
      </div>

      {insights.length > 0 && (
        <section className="insights">
          <h2>{t("insights")}</h2>
          <ul>
            {insights.map((i) => {
              const Icon = i.tone === "warn" ? AlertTriangle : i.tone === "good" ? TrendingUp : Lightbulb;
              const body = (
                <>
                  <Icon size={16} aria-hidden /> <span>{i.text}</span>
                </>
              );
              return (
                <li key={i.text} className={`insight insight--${i.tone}`}>
                  {i.href ? <Link href={i.href}>{body}</Link> : body}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <h2 className="dash-title">{t("work.title")}</h2>
      <div className="kpis">
        <Kpi label={t("work.new")} value={n.format(w.new)} href="/admin/applications?status=new" tone={w.new ? "warn" : undefined} />
        <Kpi label={t("work.inProgress")} value={n.format(w.in_progress)} href="/admin/applications?status=in_progress" />
        <Kpi label={t("work.stale")} value={n.format(w.stale)} href="/admin/applications?stale=1" tone={w.stale ? "warn" : "ok"} />
        <Kpi
          label={t("work.period")}
          value={n.format(w.period)}
          delta={<Delta now={w.period} before={w.period_prev} />}
          hint={t("work.split", { responses: w.responses, callbacks: w.callbacks })}
          href="/admin/applications"
        />
        <Kpi label={t("work.closed")} value={`${n.format(w.done)} / ${n.format(w.rejected)}`} hint={t("work.closedHint")} />
        <Kpi label={ts("activeListings")} value={n.format(d.listings.active)} hint={t("work.drafts", { count: d.listings.drafts })} href="/admin/listings" />
      </div>
      {d.stale.length > 0 && (
        <ul className="stale-list">
          {d.stale.map((s) => (
            <li key={s.id}>
              <Link href={`/admin/applications/${s.id}`}>{s.name}</Link>{" "}
              <span className="muted small">
                {ta(`status.${STATUSES[s.status]}`)} · {t("work.hoursAgo", { hours: ago(s.updated_at) })}
              </span>
            </li>
          ))}
        </ul>
      )}

      <h2 className="dash-title">{t("traffic.title")}</h2>
      <div className="kpis">
        <Kpi label={t("traffic.visitors")} value={n.format(tr.visitors)} delta={<Delta now={tr.visitors} before={prev.visitors} />} />
        <Kpi label={t("traffic.sessions")} value={n.format(tr.sessions)} delta={<Delta now={tr.sessions} before={prev.sessions} />} hint={t("traffic.pageviews", { count: tr.pageviews })} />
        <Kpi label={t("traffic.avgTime")} value={duration(tr.avg_session_sec)} delta={<Delta now={tr.avg_session_sec} before={prev.avg_session_sec} />} />
        <Kpi label={t("traffic.bounce")} value={pctText(bounceRate)} delta={<Delta now={bounceRate} before={pct(prev.bounces, prev.sessions)} invert />} hint={t("traffic.bounceHint")} />
        <Kpi label={t("traffic.applications")} value={n.format(tr.sent)} delta={<Delta now={tr.sent} before={prev.sent} />} />
        <Kpi label={t("traffic.conversion")} value={pctText(conversion)} delta={<Delta now={conversion} before={pct(prev.sent, prev.sessions)} />} hint={t("traffic.conversionHint")} />
      </div>

      <div className="dash-grid dash-grid--wide">
        <Panel title={t("chart.title")}>
          <DailyChart days={d.daily} labels={{ visitors: t("chart.visitors"), applications: t("chart.applications") }} locale={locale} />
        </Panel>
        <Panel title={t("funnel.title")}>
          <ol className="funnel">
            {funnel.map(([label, value], i) => (
              <li key={label}>
                <div className="bars__row">
                  <span>{label}</span>
                  <span className="bars__value">
                    {n.format(value)} <span className="muted small">{pctText(pct(value, funnel[0][1]))}</span>
                  </span>
                </div>
                <span className="bars__track">
                  <span className="bars__fill" style={{ width: `${pct(value, funnel[0][1])}%` }} />
                </span>
                {i > 0 && funnel[i - 1][1] > 0 && (
                  <span className="funnel__drop">{t("funnel.lost", { percent: pctText(Math.max(0, 100 - pct(value, funnel[i - 1][1]))) })}</span>
                )}
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <div className="dash-grid">
        <Panel title={t("sources.title")}>
          <table className="admin-table dash-table">
            <thead>
              <tr>
                <th>{t("sources.source")}</th>
                <th className="num">{t("col.visitors")}</th>
                <th className="num">{t("col.applications")}</th>
                <th className="num">{t("col.conversion")}</th>
              </tr>
            </thead>
            <tbody>
              {d.sources.map((s) => (
                <tr key={s.source}>
                  <td>{sourceLabel(s.source)}</td>
                  <td className="num">{n.format(s.visitors)}</td>
                  <td className="num">{n.format(s.applications)}</td>
                  <td className="num">{pctText(pct(s.applications, s.visitors))}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {d.sources.length === 0 && <p className="muted small">{t("empty")}</p>}
        </Panel>

        <Panel title={t("links.title")} action={<Link href="/admin/links" className="text-link small">{t("links.all")}</Link>}>
          {d.campaigns.length === 0 ? (
            <p className="muted small">
              {t("links.empty")} <Link href="/admin/links">{t("links.create")}</Link>
            </p>
          ) : (
            <table className="admin-table dash-table">
              <thead>
                <tr>
                  <th>{t("links.name")}</th>
                  <th className="num">{t("col.clicks")}</th>
                  <th className="num">{t("col.applications")}</th>
                  <th className="num">{t("col.perApplication")}</th>
                </tr>
              </thead>
              <tbody>
                {d.campaigns.map((c) => (
                  <tr key={c.id}>
                    <td>
                      {c.name}
                      <div className="muted small">/go/{c.code}</div>
                    </td>
                    <td className="num">{n.format(c.clicks)}</td>
                    <td className="num">{n.format(c.applications)}</td>
                    <td className="num">{c.cost && c.applications ? euro.format(Number(c.cost) / c.applications) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel title={t("listings.top")}>
          {d.top_listings.length === 0 ? (
            <p className="muted small">{t("empty")}</p>
          ) : (
            <table className="admin-table dash-table">
              <thead>
                <tr>
                  <th>{t("listings.listing")}</th>
                  <th className="num">{t("col.views")}</th>
                  <th className="num">{t("col.applications")}</th>
                  <th className="num">{t("col.conversion")}</th>
                </tr>
              </thead>
              <tbody>{d.top_listings.map(listingRow)}</tbody>
            </table>
          )}
        </Panel>

        <Panel title={t("listings.unanswered")}>
          <p className="muted small">{t("listings.unansweredHint")}</p>
          {d.unanswered_listings.length === 0 ? (
            <p className="muted small">{t("listings.allGood")}</p>
          ) : (
            <table className="admin-table dash-table">
              <thead>
                <tr>
                  <th>{t("listings.listing")}</th>
                  <th className="num">{t("col.views")}</th>
                  <th className="num">{t("col.applications")}</th>
                  <th className="num">{t("col.conversion")}</th>
                </tr>
              </thead>
              <tbody>{d.unanswered_listings.map(listingRow)}</tbody>
            </table>
          )}
        </Panel>

        <Panel title={t("demand.categories")}>
          <Bars rows={d.by_category.map((r) => ({ key: r.name, label: r.name, value: r.count }))} format={n.format} empty={t("empty")} />
        </Panel>
        <Panel title={t("demand.cities")}>
          <Bars rows={d.by_city.map((r) => ({ key: r.name, label: r.name, value: r.count }))} format={n.format} empty={t("empty")} />
        </Panel>

        <Panel title={t("search.top")}>
          <Bars rows={d.searches.map((r) => ({ key: r.q, label: r.q, value: r.count }))} format={n.format} empty={t("empty")} />
        </Panel>
        <Panel title={t("search.misses")} id="misses">
          <p className="muted small">{t("search.missesHint")}</p>
          <Bars
            rows={d.misses.map((r) => ({
              key: `${r.lang}:${r.q}`,
              label: (
                <>
                  {r.q} <span className="muted small">{r.lang === "uk" ? "UA" : r.lang.toUpperCase()}</span>
                </>
              ),
              value: r.hits,
            }))}
            format={n.format}
            empty={t("empty")}
          />
        </Panel>

        <Panel title={t("pages.landing")}>
          <p className="muted small">{t("pages.landingHint")}</p>
          <Bars rows={d.landing.map((r) => ({ key: r.path, label: <PathLink path={r.path} />, value: r.sessions }))} format={n.format} empty={t("empty")} />
        </Panel>
        <Panel title={t("pages.exits")}>
          <p className="muted small">{t("pages.exitsHint")}</p>
          <Bars rows={d.exits.map((r) => ({ key: r.path, label: <PathLink path={r.path} />, value: r.sessions }))} format={n.format} empty={t("empty")} />
        </Panel>

        <Panel title={t("audience.devices")}>
          <Bars
            rows={d.devices.map((r) => ({ key: r.key, label: t(`device.${r.key as "mobile"}`), value: r.visitors, extra: <span className="muted small"> · {pctText(pct(r.visitors, tr.visitors))}</span> }))}
            total={tr.visitors}            format={n.format}
            empty={t("empty")}
          />
        </Panel>
        <Panel title={t("audience.langs")}>
          <Bars
            rows={d.langs.map((r) => ({ key: r.key, label: r.key === "uk" ? "UA" : r.key.toUpperCase(), value: r.visitors, extra: <span className="muted small"> · {pctText(pct(r.visitors, tr.visitors))}</span> }))}
            total={tr.visitors}            format={n.format}
            empty={t("empty")}
          />
        </Panel>
      </div>
    </>
  );
}

function PathLink({ path }: { path: string }) {
  return (
    <a href={path} target="_blank" rel="noopener" className="path-link">
      {decodeURIComponent(path) || "/"}
    </a>
  );
}
