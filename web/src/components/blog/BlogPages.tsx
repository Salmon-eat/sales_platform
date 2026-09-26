import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { RichText } from "@/components/content/RichText";
import type { Locale } from "@/i18n/routing";
import { ApiError, apiFetch } from "@/lib/api";
import { blogPath } from "@/lib/routes";
import { absoluteUrl, jsonLd } from "@/lib/seo";
import type { BlogPost, BlogPostFull } from "@/lib/types";

type Page = { items: BlogPost[]; total: number; page: number; per_page: number };

const EMPTY: Page = { items: [], total: 0, page: 1, per_page: 12 };

async function list(locale: Locale): Promise<Page> {
  return apiFetch<Page>(`/posts?lang=${locale}`, { revalidate: 300 }).catch(() => EMPTY);
}

async function one(locale: Locale, slug: string): Promise<BlogPostFull> {
  try {
    return await apiFetch<BlogPostFull>(`/posts/${encodeURIComponent(slug)}?lang=${locale}`, {
      revalidate: 300,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function blogMetadata(locale: Locale): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "blog" });
  return {
    title: t("title"),
    description: t("subtitle"),
    alternates: { canonical: absoluteUrl(blogPath(locale)) },
  };
}

export async function postMetadata(locale: Locale, slug: string): Promise<Metadata> {
  const post = await one(locale, slug);
  return {
    title: post.title,
    description: post.excerpt || undefined,
    alternates: { canonical: absoluteUrl(blogPath(locale, post.slug)) },
    openGraph: { title: post.title, type: "article", publishedTime: post.published_at ?? undefined },
  };
}

/** The list of articles: what people search for before they search for an ad. */
export async function BlogList({ locale }: { locale: Locale }) {
  const t = await getTranslations("blog");
  const data = await list(locale);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "Europe/Madrid" });

  return (
    <div className="container static-page">
      <section className="seller-head">
        <h1>{t("title")}</h1>
        <p className="muted">{t("subtitle")}</p>
      </section>

      {data.items.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <ul className="post-list">
          {data.items.map((post) => (
            <li key={post.id} className="post-card">
              {post.cover && (
                <span className="post-card__cover">
                  <img src={post.cover} alt="" loading="lazy" />
                </span>
              )}
              <div>
                <h2>
                  <Link href={blogPath(locale, post.slug)} className="listing-link">
                    {post.title}
                  </Link>
                </h2>
                {post.published_at && (
                  <p className="muted small">{date.format(new Date(post.published_at))}</p>
                )}
                {post.excerpt && <p className="post-card__excerpt">{post.excerpt}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** One article. */
export async function PostPage({ locale, slug }: { locale: Locale; slug: string }) {
  const t = await getTranslations("blog");
  const post = await one(locale, slug);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "Europe/Madrid" });

  return (
    <div className="container static-page static-page--narrow">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd({
          "@context": "https://schema.org",
          "@type": "Article",
          headline: post.title,
          description: post.excerpt || undefined,
          datePublished: post.published_at ?? undefined,
          dateModified: post.updated_at,
          inLanguage: post.lang,
          mainEntityOfPage: absoluteUrl(blogPath(locale, post.slug)),
          publisher: { "@type": "Organization", name: "Citobazar" },
        })}
      />
      <nav className="breadcrumbs">
        <Link href={blogPath(locale)}>{t("title")}</Link>
        <span aria-hidden>›</span>
        <span>{post.title}</span>
      </nav>

      <article className="post">
        <h1>{post.title}</h1>
        {post.published_at && <p className="muted small">{date.format(new Date(post.published_at))}</p>}
        {post.cover && <img className="post__cover" src={post.cover} alt="" />}
        <RichText text={post.body} />
      </article>
    </div>
  );
}
