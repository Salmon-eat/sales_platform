import { Check, Globe, RefreshCw, X } from "lucide-react";
import { Fragment } from "react";

import { adminT } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";

import { collectWords, decideWord } from "../../search-words-actions";

type Proposal = {
  id: number;
  word: string;
  lang: string;
  searches: number;
  opened: number;
  status: string;
  category_id: number | null;
  category: string | null;
  section: string | null;
};

/** The same thing in four languages, as Wikidata knows it. */
type Lookup = {
  id: string;
  title: string;
  description: string;
  url: string;
  words: Record<string, string[]>;
};

/**
 * Words the site wants to learn.
 *
 * Every night it looks at what people searched for in vain and which ad they opened next. When many
 * separate visits point at the same category it adds the word by itself; what is left is here,
 * because a wrong synonym sticks to every ad in the category.
 */
export default async function SearchWordsPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; error?: string; status?: string; lookup?: string }>;
}) {
  const { ok, error, status, lookup } = await searchParams;
  const t = await adminT("searchWords");
  const shown = status === "added" || status === "ignored" ? status : "new";
  const proposals = await adminFetch<Proposal[]>(`/admin/search-words/proposals?status=${shown}`);
  // what Wikidata says this word is, fetched only for the row somebody asked about
  const asked = Number(lookup) || 0;
  const found = asked
    ? await adminFetch<{ found: Lookup | null }>(`/admin/search-words/lookup?proposal_id=${asked}`)
        .then((r) => r.found)
        .catch(() => null)
    : null;

  return (
    <section className="admin-section">
      <header className="admin-head">
        <div>
          <h1>{t("title")}</h1>
          <p className="muted">{t("subtitle")}</p>
        </div>
        <form action={collectWords}>
          <button type="submit" className="btn btn--outline">
            <RefreshCw size={14} aria-hidden /> {t("collect")}
          </button>
        </form>
      </header>

      {ok && <p className="notice notice--ok">{t("done")}</p>}
      {error && <p className="notice notice--error">{t("failed")}</p>}

      <nav className="admin-tabs">
        {(["new", "added", "ignored"] as const).map((key) => (
          <a
            key={key}
            href={`/admin/search-words?status=${key}`}
            className={shown === key ? "admin-tab admin-tab--active" : "admin-tab"}
          >
            {t(`tab_${key}`)}
          </a>
        ))}
      </nav>

      {proposals.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("word")}</th>
              <th>{t("category")}</th>
              <th>{t("evidence")}</th>
              {shown === "new" && <th />}
            </tr>
          </thead>
          <tbody>
            {proposals.map((p) => (
              <Fragment key={p.id}>
              <tr>
                <td>
                  <strong>{p.word}</strong> <span className="muted small">{p.lang}</span>
                </td>
                <td>
                  {p.category ? (
                    <>
                      {p.category}
                      {p.section && <span className="muted small"> · {p.section}</span>}
                    </>
                  ) : (
                    <span className="muted">{t("noGuess")}</span>
                  )}
                </td>
                <td className="muted small">{t("counts", { searches: p.searches, opened: p.opened })}</td>
                {shown === "new" && (
                  <td className="admin-table__actions">
                    <a
                      href={`/admin/search-words?status=new&lookup=${p.id}`}
                      className="btn btn--outline btn--small"
                    >
                      <Globe size={13} aria-hidden /> {t("lookUp")}
                    </a>
                    {p.category_id && (
                      <form action={decideWord}>
                        <input type="hidden" name="id" value={p.id} />
                        <input type="hidden" name="action" value="add" />
                        <button type="submit" className="btn btn--primary btn--small">
                          <Check size={13} aria-hidden /> {t("add")}
                        </button>
                      </form>
                    )}
                    <form action={decideWord}>
                      <input type="hidden" name="id" value={p.id} />
                      <input type="hidden" name="action" value="ignore" />
                      <button type="submit" className="btn btn--outline btn--small">
                        <X size={13} aria-hidden /> {t("ignore")}
                      </button>
                    </form>
                  </td>
                )}
              </tr>
              {asked === p.id && (
                <tr className="lookup-row">
                  <td colSpan={shown === "new" ? 4 : 3}>
                    {found === null ? (
                      <p className="muted">{t("lookupNothing", { word: p.word })}</p>
                    ) : (
                      <div className="lookup">
                        <p>
                          <strong>{found.title}</strong>{" "}
                          <span className="muted small">{found.description}</span>{" "}
                          <a href={found.url} target="_blank" rel="noreferrer noopener" className="muted small">
                            {found.id}
                          </a>
                        </p>
                        <dl className="lookup__words">
                          {Object.entries(found.words).map(([code, names]) => (
                            <div key={code}>
                              <dt>{code}</dt>
                              <dd>{names.join(", ")}</dd>
                            </div>
                          ))}
                        </dl>
                        {p.category_id && (
                          <form action={decideWord}>
                            <input type="hidden" name="id" value={p.id} />
                            <input type="hidden" name="action" value="add" />
                            <input type="hidden" name="words" value={JSON.stringify(found.words)} />
                            <button type="submit" className="btn btn--primary btn--small">
                              <Check size={13} aria-hidden /> {t("addAll", { category: p.category ?? "" })}
                            </button>
                          </form>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}

      <p className="muted small">{t("note")}</p>
    </section>
  );
}
