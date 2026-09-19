import "server-only";

import { cache } from "react";

import type {
  ContentBlock,
  Lang,
  ListingDetail,
  ListingStats,
  LocationRef,
  ResolveOut,
  SearchResponse,
  SitemapPage,
  Taxonomy,
} from "./types";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    /** FastAPI `detail`: a string or a list of validation errors. */
    public readonly detail?: unknown,
  ) {
    super(message);
  }
}

type FetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
  /** Seconds for ISR data cache; `false` = always fresh (SSR). */
  revalidate?: number | false;
  /** Admin UI language: names of professions, cities etc. come back in it. */
  lang?: string;
  /** The visitor's IP (from Caddy), so per-IP limits such as sign-in attempts apply to them, not to us. */
  clientIp?: string;
};

/** `path` is relative to the API version root, e.g. "/auth/me" -> /v1/auth/me. */
export async function apiFetch<T>(
  path: string,
  { method = "GET", body, token, revalidate = false, lang, clientIp }: FetchOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  if (lang) headers["Accept-Language"] = lang;
  if (clientIp) headers["X-Forwarded-For"] = clientIp;

  const res = await fetch(`${API_URL}/v1${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    ...(revalidate === false || token ? { cache: "no-store" } : { next: { revalidate } }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, `${method} /v1${path} -> ${res.status}`, body?.detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/** Search with filters and facets. `params` = the page query (tier 2/3, q, sort, page, category, location). */
/** `revalidate` > 0 only for static pages (the home catalog); list pages are rendered per request. */
export const searchListings = cache((lang: string, section: string, params: [string, string][], revalidate: number | false = false) => {
  const qs = new URLSearchParams([["lang", lang], ["section", section], ["per_page", "20"], ...params]);
  return apiFetch<SearchResponse>(`/listings?${qs}`, { revalidate });
});

/** Path without the language prefix -> what the page is. Memoized per request (metadata + page). */
export const resolvePath = cache((lang: string, path: string) =>
  apiFetch<ResolveOut>(`/resolve?lang=${lang}&path=${encodeURIComponent(path)}`, { revalidate: 60 }),
);

export const getListingDetail = cache((id: number, lang: string) =>
  apiFetch<ListingDetail>(`/listings/${id}?lang=${lang}`, { revalidate: 60 }),
);

export const getContent = cache((key: string, lang: string) =>
  apiFetch<ContentBlock>(`/content/${key}?lang=${lang}`, { revalidate: 300 }),
);

/** Sitemap pages are large (up to 40k URLs), so they bypass the data cache; the route handler caches the XML. */
export function getSitemapPage(lang: string, kind: "lists" | "listings", page = 1) {
  return apiFetch<SitemapPage>(`/sitemaps/${lang}/${kind}?page=${page}`);
}

export function getSitemapIndex() {
  return apiFetch<Record<Lang, { lists: number; listings: number }>>("/sitemaps/index", { revalidate: 3600 });
}

export function getListingStats(category?: string) {
  return apiFetch<ListingStats>(`/listings/stats${category ? `?category=${category}` : ""}`, { revalidate: 60 });
}

export function getTaxonomy(lang: string) {
  return apiFetch<Taxonomy>(`/taxonomy?lang=${lang}`, { revalidate: 300 });
}

export function getPopularLocations(lang: string, limit = 50) {
  return apiFetch<LocationRef[]>(`/locations/popular?lang=${lang}&limit=${limit}`, { revalidate: 3600 });
}

/** For pages that must still render (build time, API hiccup) — ISR will refresh them later. */
export async function orFallback<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch (error) {
    console.warn(`[api] using fallback: ${error instanceof Error ? error.message : error}`);
    return fallback;
  }
}
