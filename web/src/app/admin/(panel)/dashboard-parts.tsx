import Link from "next/link";
import type { ReactNode } from "react";

/** Change against the previous period of the same length; hidden when there is nothing to compare. */
export function Delta({ now, before, invert = false }: { now: number; before: number; invert?: boolean }) {
  if (!before) return null;
  const change = Math.round(((now - before) / before) * 100);
  if (change === 0) return <span className="delta">±0%</span>;
  const good = invert ? change < 0 : change > 0;
  return (
    <span className={good ? "delta delta--up" : "delta delta--down"}>
      {change > 0 ? "▲" : "▼"} {Math.abs(change)}%
    </span>
  );
}

export function Kpi({
  label,
  value,
  hint,
  delta,
  href,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  delta?: ReactNode;
  href?: string;
  tone?: "warn" | "ok";
}) {
  const body = (
    <>
      <span className="kpi__label">{label}</span>
      <strong className="kpi__value">{value}</strong>
      <span className="kpi__foot">
        {delta}
        {hint && <span className="muted">{hint}</span>}
      </span>
    </>
  );
  const className = `admin-card kpi${tone ? ` kpi--${tone}` : ""}${href ? " admin-card--link" : ""}`;
  return href ? (
    <Link href={href} className={className}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  );
}

/** Horizontal bars: the line is the row's share of the total (all rows unless given), not of the largest row. */
export function Bars({
  rows,
  format,
  empty,
  total,
}: {
  rows: { key: string; label: ReactNode; value: number; extra?: ReactNode }[];
  format: (n: number) => string;
  empty: string;
  total?: number;
}) {
  if (rows.length === 0) return <p className="muted small">{empty}</p>;
  const max = Math.max(total ?? rows.reduce((sum, r) => sum + r.value, 0), 1);
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li key={r.key}>
          <div className="bars__row">
            <span className="bars__label">{r.label}</span>
            <span className="bars__value">
              {format(r.value)}
              {r.extra}
            </span>
          </div>
          <span className="bars__track">
            <span className="bars__fill" style={{ width: `${Math.min(100, (r.value / max) * 100)}%` }} />
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Visitors per day (bars) with applications per day (dots on a second scale). */
export function DailyChart({
  days,
  labels,
  locale,
}: {
  days: { day: string; visitors: number; applications: number }[];
  labels: { visitors: string; applications: string };
  locale: string;
}) {
  const W = 760;
  const H = 180;
  const pad = { top: 12, bottom: 22, left: 4, right: 4 };
  const maxV = Math.max(...days.map((d) => d.visitors), 1);
  const maxA = Math.max(...days.map((d) => d.applications), 1);
  const step = (W - pad.left - pad.right) / Math.max(days.length, 1);
  const inner = H - pad.top - pad.bottom;
  const fmt = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", timeZone: "UTC" });
  const every = Math.ceil(days.length / 8);
  const points = days.map((d, i) => [pad.left + step * (i + 0.5), pad.top + inner - (d.applications / maxA) * inner] as const);

  return (
    <figure className="daily-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${labels.visitors}, ${labels.applications}`}>
        {days.map((d, i) => {
          const h = (d.visitors / maxV) * inner;
          return (
            <g key={d.day}>
              <rect
                x={pad.left + step * i + step * 0.15}
                y={pad.top + inner - h}
                width={step * 0.7}
                height={Math.max(h, 1)}
                rx={2}
                className="daily-chart__bar"
              >
                <title>{`${fmt.format(new Date(d.day))}: ${d.visitors} · ${d.applications}`}</title>
              </rect>
              {i % every === 0 && (
                <text x={pad.left + step * (i + 0.5)} y={H - 6} textAnchor="middle" className="daily-chart__axis">
                  {fmt.format(new Date(d.day))}
                </text>
              )}
            </g>
          );
        })}
        <polyline points={points.map((p) => p.join(",")).join(" ")} className="daily-chart__line" />
        {points.map(([x, y], i) => (
          <circle key={days[i].day} cx={x} cy={y} r={2.6} className="daily-chart__dot" />
        ))}
      </svg>
      <figcaption className="daily-chart__legend">
        <span className="legend legend--bar">{labels.visitors}</span>
        <span className="legend legend--line">{labels.applications}</span>
      </figcaption>
    </figure>
  );
}

export function Panel({ title, action, id, children }: { title: string; action?: ReactNode; id?: string; children: ReactNode }) {
  return (
    <section className="admin-card dash-panel" id={id}>
      <div className="dash-panel__head">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
