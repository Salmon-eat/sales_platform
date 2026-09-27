import { Check, RefreshCw, X } from "lucide-react";

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
  searchParams: Promise<{ ok?: string; error?: string; status?: string }>;
}) {
  const { ok, error, status } = await searchParams;
  const t = await adminT("searchWords");
  const shown = status === "added" || status === "ignored" ? status : "new";
  const proposals = await adminFetch<Proposal[]>(`/admin/search-words/proposals?status=${shown}`);

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
              <tr key={p.id}>
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
            ))}
          </tbody>
        </table>
      )}

      <p className="muted small">{t("note")}</p>
    </section>
  );
}
