import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";

import { deletePost, savePost } from "../../posts-actions";

type Post = {
  id: number;
  slug: string;
  lang: string;
  title: string;
  excerpt: string;
  cover: string | null;
  status: string;
  published_at: string | null;
  updated_at: string;
  body?: string;
};

const LANGS = ["es", "en", "uk", "ru"] as const;

/** Writing an article. One article is one language, written by hand — never a machine translation. */
export default async function PostsPage({
  searchParams,
}: {
  searchParams: Promise<{ edit?: string; ok?: string; error?: string }>;
}) {
  const { edit, ok, error } = await searchParams;
  const t = await adminT("posts");
  const locale = await getAdminLocale();
  const posts = await adminFetch<Post[]>("/admin/posts");
  const editing = /^\d+$/.test(edit ?? "")
    ? await adminFetch<Post>(`/admin/posts/${edit}`).catch(() => null)
    : null;
  const when = new Intl.DateTimeFormat(locale, { dateStyle: "short", timeZone: "Europe/Madrid" });

  return (
    <section className="admin-section">
      <header className="admin-head">
        <div>
          <h1>{t("title")}</h1>
          <p className="muted">{t("subtitle")}</p>
        </div>
        <span className="admin-count">{t("count", { count: posts.length })}</span>
      </header>

      {ok && <p className="notice notice--ok">{t("saved")}</p>}
      {error && <p className="notice notice--error">{t("failed")}</p>}

      <form action={savePost} className="post-form">
        {editing && <input type="hidden" name="id" value={editing.id} />}
        <h2 className="admin-subhead">{editing ? t("editing", { title: editing.title }) : t("newPost")}</h2>
        <div className="field-row">
          <label className="field">
            <span>{t("postTitle")}</span>
            <input name="title" required minLength={3} maxLength={200} defaultValue={editing?.title ?? ""} />
          </label>
          <label className="field">
            <span>{t("lang")}</span>
            <select name="lang" defaultValue={editing?.lang ?? "es"}>
              {LANGS.map((code) => (
                <option key={code} value={code}>
                  {code.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("slug")}</span>
            <input name="slug" maxLength={160} pattern="[a-z0-9-]*" defaultValue={editing?.slug ?? ""} placeholder={t("slugHint")} />
          </label>
        </div>
        <label className="field">
          <span>{t("excerpt")}</span>
          <input name="excerpt" maxLength={300} defaultValue={editing?.excerpt ?? ""} />
        </label>
        <label className="field">
          <span>{t("body")}</span>
          <textarea name="body" rows={14} defaultValue={editing?.body ?? ""} placeholder={t("bodyHint")} />
        </label>
        <div className="field-row">
          <label className="field">
            <span>{t("cover")}</span>
            <input name="cover" maxLength={200} defaultValue={editing?.cover ?? ""} placeholder="/media/…" />
          </label>
          <label className="field">
            <span>{t("status")}</span>
            <select name="status" defaultValue={editing?.status ?? "draft"}>
              <option value="draft">{t("status_draft")}</option>
              <option value="published">{t("status_published")}</option>
            </select>
          </label>
        </div>
        <button type="submit" className="btn btn--primary">
          {editing ? t("save") : t("create")}
        </button>
      </form>

      {posts.length > 0 && (
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("postTitle")}</th>
              <th>{t("lang")}</th>
              <th>{t("status")}</th>
              <th>{t("updated")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {posts.map((post) => (
              <tr key={post.id}>
                <td>
                  {post.title}
                  <div className="muted small">/{post.lang}/blog/{post.slug}</div>
                </td>
                <td>{post.lang.toUpperCase()}</td>
                <td>
                  <span className={`badge badge--${post.status === "published" ? "active" : "pending"}`}>
                    {t(`status_${post.status}` as "status_draft")}
                  </span>
                </td>
                <td className="muted small">{when.format(new Date(post.updated_at))}</td>
                <td>
                  <div className="admin-row-actions">
                    <a className="btn btn--outline btn--sm" href={`/admin/posts?edit=${post.id}`}>
                      {t("edit")}
                    </a>
                    <form action={deletePost}>
                      <input type="hidden" name="id" value={post.id} />
                      <button type="submit" className="link-button">
                        {t("delete")}
                      </button>
                    </form>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
