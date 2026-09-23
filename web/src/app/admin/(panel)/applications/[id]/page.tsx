import Link from "next/link";
import { notFound } from "next/navigation";
import { Fragment } from "react";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { ApiError } from "@/lib/api";
import { adminFetch, getCurrentUser } from "@/lib/auth";
import type { AdminApplicationDetail } from "@/lib/types";

import { erasePerson, replyInChat } from "../../../actions";
import { ConfirmButton } from "../../links/ConfirmButton";
import { StatusSelect } from "../StatusSelect";
import { STATUSES } from "../statuses";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<{ erased?: string }> };

export default async function ApplicationPage({ params, searchParams }: Props) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  let a: AdminApplicationDetail;
  try {
    a = await adminFetch<AdminApplicationDetail>(`/admin/applications/${id}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const t = await adminT("applications");
  const tc = await adminT("common");
  const tl = await adminT("listings");
  const dateTime = new Intl.DateTimeFormat(await getAdminLocale(), {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });
  const fmt = (iso: string) => dateTime.format(new Date(iso));
  const statuses = Object.entries(STATUSES).map(([value, key]) => [value, t(`status.${key}`)] as const);
  const utm = Object.entries(a.utm);
  const { erased } = await searchParams;
  const isAdmin = (await getCurrentUser())?.role === "admin";

  return (
    <>
      <nav className="breadcrumbs">
        <Link href={a.bot ? "/admin/applications?from=bot" : "/admin/applications"}>
          {t("title")} · {t(a.bot ? "tabs.bot" : "tabs.site")}
        </Link>
        <span aria-hidden>›</span>
        <span>#{a.id}</span>
      </nav>
      <div className="admin-head">
        <h1>{a.name}</h1>
        <StatusSelect key={a.status} id={a.id} value={a.status} options={statuses} label={t("table.status")} />
      </div>

      {erased && <p className="notice notice--ok">{t("gdpr.erased", { count: Number(erased) || 1 })}</p>}
      {a.anonymized_at && !erased && <p className="notice">{t("gdpr.anonymizedAt", { date: fmt(a.anonymized_at) })}</p>}

      <div className="app-detail">
        <section className="admin-card">
          <h2>{t("detail.request")}</h2>
          {a.listing ? (
            <>
              <span className="badge">{t("kind.response")}</span>
              <Link href={`/admin/listings/${a.listing.id}`} className="app-detail__job">
                {a.listing.title}
              </Link>
              <div className="inline-form">
                <span className={`status status--${a.listing.status}`}>{tl(`status.${a.listing.status}`)}</span>
                <span className="muted">
                  №{a.listing.id} · {a.listing.location_name ?? t("row.noCity")}
                </span>
              </div>
            </>
          ) : a.bot ? (
            <>
              <span className="badge badge--tg">{t("kind.telegram")}</span>
              <p className="app-detail__job">{a.bot.title ?? a.category_name}</p>
              {a.bot.card && (
                <>
                  <h3>{t("bot.card")}</h3>
                  <pre className="app-detail__card">{a.bot.card}</pre>
                </>
              )}
              {a.bot.topic_url && (
                <a href={a.bot.topic_url} target="_blank" rel="noopener noreferrer" className="btn btn--ghost-dark btn--sm">
                  {t("bot.topic")}
                </a>
              )}
            </>
          ) : (
            <>
              <span className={a.source === "chat" ? "badge badge--chat" : "badge badge--muted"}>{t(a.source === "chat" ? "kind.message" : "kind.callback")}</span>
              <dl className="app-detail__dl">
                <dt>{t("table.sector")}</dt>
                <dd>{a.category_name ?? t("row.anyCategory")}</dd>
                <dt>{t("table.city")}</dt>
                <dd>{a.location_name ?? t("row.noCity")}</dd>
              </dl>
            </>
          )}
          {a.comment && (
            <>
              <h3>{t("table.comment")}</h3>
              <p className="app-detail__comment">{a.comment}</p>
            </>
          )}
          {a.answers.length > 0 && (
            <>
              <h3>{t("detail.answers")}</h3>
              <dl className="app-detail__dl app-detail__answers">
                {a.answers.map((x) => (
                  <Fragment key={x.question}>
                    <dt>{x.question}</dt>
                    <dd>{x.answer}</dd>
                  </Fragment>
                ))}
              </dl>
            </>
          )}
          {a.files.length > 0 && (
            <>
              <h3>{t("detail.cv")}</h3>
              {a.files.map((f) => (
                <p key={f.id} className="app-detail__file">
                  <a href={`/admin/api/applications/${a.id}/files/${f.id}`} className="btn btn--ghost-dark btn--sm" download>
                    {t("detail.cvDownload")}
                  </a>{" "}
                  <span className="muted small">
                    {f.filename} · {Math.max(1, Math.round(f.size / 1024))} KB
                  </span>
                </p>
              ))}
            </>
          )}
        </section>

        <section className="admin-card">
          <h2>{t("detail.contact")}</h2>
          <dl className="app-detail__dl">
            <dt>{t("detail.phone")}</dt>
            <dd>{a.phone ? <a href={`tel:${a.phone}`}>{a.phone}</a> : <span className="muted">{t("row.noPhone")}</span>}</dd>
            {a.bot ? (
              <>
                <dt>{t("bot.username")}</dt>
                <dd>
                  {a.bot.username ? (
                    <a href={`https://t.me/${a.bot.username}`} target="_blank" rel="noopener noreferrer">
                      @{a.bot.username}
                    </a>
                  ) : (
                    "—"
                  )}
                </dd>
                <dt>{t("bot.number")}</dt>
                <dd>№{a.bot.app_id}</dd>
                <dt>{t("bot.manager")}</dt>
                <dd>{a.bot.manager_name ?? <span className="muted">{t("bot.noManager")}</span>}</dd>
              </>
            ) : (
              <>
                <dt>{t("table.contact")}</dt>
                <dd>{a.source === "chat" && !a.phone ? t("kind.message") : t(`messenger.${a.messenger}`)}</dd>
                <dt>{t("table.inSpain")}</dt>
                <dd>{a.in_spain === null ? "—" : a.in_spain ? tc("yes") : tc("no")}</dd>
              </>
            )}
            <dt>{t(a.bot ? "detail.lang" : "detail.siteLang")}</dt>
            <dd>{a.lang.toUpperCase()}</dd>
            <dt>{t("table.date")}</dt>
            <dd>{fmt(a.created_at)}</dd>
            {!a.bot && (
              <>
                <dt>{t("gdpr.consent")}</dt>
                <dd>{t("gdpr.consentValue", { date: fmt(a.consent_at), version: a.consent_version })}</dd>
              </>
            )}
            {utm.length > 0 && (
              <>
                <dt>{t("detail.utm")}</dt>
                <dd className="small">
                  {utm.map(([k, v]) => (
                    <div key={k}>
                      {k}: {v}
                    </div>
                  ))}
                </dd>
              </>
            )}
          </dl>
        </section>
      </div>

      {(a.source === "chat" || a.bot) && (
        <section className="admin-section">
          <h2>{t(a.bot ? "chat.titleBot" : "chat.title")}</h2>
          <p className="muted small">{t(a.bot ? "chat.hintBot" : "chat.hint")}</p>
          <ol className="chat-thread">
            {a.messages.map((m) => (
              <li key={m.id} className={`chat-msg chat-msg--${m.author}`}>
                <span className="chat-msg__who">
                  {m.author === "visitor"
                    ? a.name
                    : m.author === "note"
                      ? `${t("chat.note")}${m.author_name ? ` · ${m.author_name}` : ""}`
                      : (m.author_name ?? t("chat.manager"))}{" "}
                  · {fmt(m.created_at)}
                  {m.delivery && m.delivery !== "delivered" && (
                    <span className={`chat-msg__delivery chat-msg__delivery--${m.delivery}`}>
                      {" "}
                      · {t(`chat.delivery.${m.delivery}`)}
                    </span>
                  )}
                </span>
                {m.content_type && m.content_type !== "text" && (
                  <span className="chat-msg__attachment">{t("chat.attachment", { type: m.content_type })}</span>
                )}
                {m.text && <p>{m.text}</p>}
              </li>
            ))}
          </ol>
          {!a.anonymized_at && (
            <form action={replyInChat} className="chat-reply">
              <input type="hidden" name="id" value={a.id} />
              <textarea name="text" required maxLength={1000} rows={3} placeholder={t("chat.placeholder")} />
              <button type="submit" className="btn btn--primary">
                {t("chat.send")}
              </button>
            </form>
          )}
        </section>
      )}

      {a.notes.length > 0 && (
        <section className="admin-section">
          <h2>{t("detail.notes")}</h2>
          <ul className="app-detail__list">
            {a.notes.map((n) => (
              <li key={n.id}>
                <span className="muted small">{fmt(n.created_at)}</span> {n.text}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="admin-section">
        <h2>{t("detail.history")}</h2>
        {a.history.length === 0 ? (
          <p className="muted">{t("detail.noHistory")}</p>
        ) : (
          <ul className="app-detail__list">
            {a.history.map((h) => (
              <li key={h.id}>
                <Link href={`/admin/applications/${h.id}`}>#{h.id}</Link>{" "}
                <span className="muted small">{fmt(h.created_at)}</span> ·{" "}
                {h.listing ? h.listing.title : (h.category_name ?? t("kind.callback"))} ·{" "}
                {t(`status.${STATUSES[h.status]}`)}
              </li>
            ))}
          </ul>
        )}
      </section>
      {/* the bot's records follow the bot's own rules: no erasure or export from the site */}
      {isAdmin && !a.anonymized_at && !a.bot && (
        <section className="admin-section gdpr-box">
          <h2>{t("gdpr.title")}</h2>
          <p className="muted small">{t("gdpr.hint", { count: a.person_applications })}</p>
          <div className="inline-form">
            <a href={`/admin/api/applications/${a.id}/person-data`} className="btn btn--ghost-dark btn--sm" download>
              {t("gdpr.export")}
            </a>
            <form action={erasePerson}>
              <input type="hidden" name="id" value={a.id} />
              <ConfirmButton question={t("gdpr.confirm", { count: a.person_applications })} className="btn btn--danger btn--sm">
                {t("gdpr.erase")}
              </ConfirmButton>
            </form>
          </div>
        </section>
      )}
    </>
  );
}