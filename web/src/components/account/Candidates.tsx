"use client";

import { Download, Phone } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { addCandidateNote, setCandidateStatus } from "@/app/[locale]/employer-actions";
import { asLocale } from "@/i18n/routing";
import type { ApplicationStatus, Candidate } from "@/lib/types";

const STATUSES: ApplicationStatus[] = ["new", "in_progress", "done", "rejected"];

/** "Answers to my vacancies": who wrote, what they can do, and where each one stands. */
export function Candidates({ initial }: { initial: Candidate[] }) {
  const t = useTranslations("candidates");
  const tr = useTranslations("resume");
  const locale = asLocale(useLocale());
  const [people, setPeople] = useState(initial);
  const [filter, setFilter] = useState<ApplicationStatus | "all">("all");
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const date = new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });

  if (people.length === 0) return null;

  const shown = filter === "all" ? people : people.filter((person) => person.status === filter);
  const replace = (updated: Candidate | null) => {
    if (updated) setPeople((current) => current.map((p) => (p.id === updated.id ? updated : p)));
  };

  async function move(id: number, status: ApplicationStatus) {
    setBusy(true);
    replace(await setCandidateStatus(id, status, locale));
    setBusy(false);
  }

  async function note(event: FormEvent<HTMLFormElement>, id: number) {
    event.preventDefault();
    const form = event.currentTarget;
    const text = String(new FormData(form).get("text") ?? "").trim();
    if (!text) return;
    setBusy(true);
    replace(await addCandidateNote(id, text, locale));
    setBusy(false);
    form.reset();
  }

  return (
    <section className="candidates">
      <div className="home-block__head">
        <h2>{t("title")}</h2>
        <div className="chips-row">
          {(["all", ...STATUSES] as const).map((key) => (
            <button
              key={key}
              type="button"
              className={filter === key ? "chip chip--on" : "chip"}
              onClick={() => setFilter(key)}
            >
              {key === "all" ? t("all") : t(`status_${key}` as "status_new")}
              <span className="facet-count">
                {key === "all" ? people.length : people.filter((p) => p.status === key).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      <ul className="candidate-list">
        {shown.map((person) => (
          <li key={person.id} className="candidate">
            <div className="candidate__head">
              <div>
                <strong>{person.name}</strong>
                {person.headline && <span className="muted"> · {person.headline}</span>}
                <div className="muted small">
                  {person.listing_title} · {date.format(new Date(person.created_at))}
                </div>
              </div>
              <span className={`badge badge--${person.status}`}>
                {t(`status_${person.status}` as "status_new")}
              </span>
            </div>

            <p className="candidate__facts">
              {person.phone && (
                <a href={`tel:${person.phone.replace(/\s/g, "")}`} className="btn btn--outline btn--sm">
                  <Phone size={14} aria-hidden /> {person.phone}
                </a>
              )}
              {person.has_cv && (
                <a href={`/api/my/candidates/${person.id}/cv`} className="btn btn--outline btn--sm">
                  <Download size={14} aria-hidden /> {t("cv")}
                </a>
              )}
              {person.experience_years !== null && (
                <span className="chip">{t("years", { count: person.experience_years })}</span>
              )}
              {person.licences.map((licence) => (
                <span key={licence} className="chip">
                  {tr(`licence_${licence}` as "licence_b")}
                </span>
              ))}
              {Object.entries(person.languages).map(([code, level]) => (
                <span key={code} className="chip">
                  {tr(`lang_${code}` as "lang_es")}: {tr(`level_${level}` as "level_a1")}
                </span>
              ))}
            </p>

            {person.comment && <p className="candidate__comment">{person.comment}</p>}
            {person.answers.length > 0 && (
              <dl className="candidate__answers">
                {person.answers.map((answer) => (
                  <div key={answer.question}>
                    <dt>{answer.question}</dt>
                    <dd>{answer.answer}</dd>
                  </div>
                ))}
              </dl>
            )}

            <div className="candidate__actions">
              {STATUSES.filter((status) => status !== person.status).map((status) => (
                <button
                  key={status}
                  type="button"
                  className="btn btn--ghost-dark btn--sm"
                  disabled={busy}
                  onClick={() => move(person.id, status)}
                >
                  {t(`move_${status}` as "move_new")}
                </button>
              ))}
              <button
                type="button"
                className="link-button"
                onClick={() => setOpen(open === person.id ? null : person.id)}
              >
                {t("notes", { count: person.notes.length })}
              </button>
            </div>

            {open === person.id && (
              <div className="candidate__notes">
                {person.notes.map((item) => (
                  <p key={item.created_at + item.text}>
                    <span className="muted small">
                      {item.author ?? "—"} · {date.format(new Date(item.created_at))}
                    </span>
                    <br />
                    {item.text}
                  </p>
                ))}
                <form onSubmit={(event) => note(event, person.id)} className="candidate__note-form">
                  <input name="text" maxLength={2000} placeholder={t("notePlaceholder")} />
                  <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>
                    {t("noteAdd")}
                  </button>
                </form>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
