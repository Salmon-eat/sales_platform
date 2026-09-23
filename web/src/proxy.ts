import { type NextRequest, NextResponse } from "next/server";
import createMiddleware from "next-intl/middleware";

import { isLocale, type Locale, localePrefix, routing, X_DEFAULT_LOCALE } from "@/i18n/routing";
import { AUTH_COOKIE } from "@/lib/auth-constants";

const intl = createMiddleware(routing);

const LOCALE_COOKIE = "NEXT_LOCALE";
const BOT_RE = /bot|crawl|spider|slurp|bingpreview|facebookexternalhit|embedly|lighthouse/i;

/**
 * "/" -> the language the visitor chose before (cookie), otherwise the site's default: Spanish in
 * production. The browser's own language is deliberately ignored: this is a Spanish site, and everybody
 * starts on the Spanish version until they pick another language in the header.
 */
function pickLocale(request: NextRequest): Locale {
  if (BOT_RE.test(request.headers.get("user-agent") ?? "")) return X_DEFAULT_LOCALE;

  const cookie = request.cookies.get(LOCALE_COOKIE)?.value;
  return isLocale(cookie) ? cookie : routing.defaultLocale;
}

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
// the word before the slug: a job ("oferta") or an ad of any other kind ("anuncio")
const CARD_RE =
  /^\/(?:es|en|ua|ru)\/[^/]+\/(?:oferta|job|vakansiia|vakansiya|anuncio|ad|oholoshennia|obyavlenie)\/[^/]*-(\d+)\/?$/;

/** spec §6: a card closed more than 90 days ago answers 410 Gone (earlier: 200 + badge, then noindex). */
async function goneResponse(pathname: string): Promise<NextResponse | null> {
  const id = CARD_RE.exec(pathname)?.[1];
  if (!id) return null;
  try {
    const res = await fetch(`${API_URL}/v1/listings/${id}/state`, { signal: AbortSignal.timeout(1500), cache: "no-store" });
    if (!res.ok) return null;
    const { state } = (await res.json()) as { state: string };
    if (state !== "gone") return null;
  } catch {
    return null; // the page itself handles API outages
  }
  const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex"><title>410</title></head><body style="font-family:system-ui;padding:48px"><h1>410</h1><p>Esta oferta ya no está disponible · Ця вакансія більше не доступна</p><p><a href="/">Citobazar</a></p></body></html>`;
  return new NextResponse(html, {
    status: 410,
    headers: { "Content-Type": "text/html; charset=utf-8", "X-Robots-Tag": "noindex" },
  });
}

function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (!origin || !host) return false;
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export default async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    // CSRF (admin spec §1): Next.js compares Origin with Host for Server Actions but lets a request
    // without Origin through; the admin refuses any changing request that is not same-origin.
    if (request.method !== "GET" && request.method !== "HEAD" && !sameOrigin(request)) {
      return new NextResponse("Forbidden", { status: 403 });
    }
    // Cheap presence check only; the token is verified against the API in the admin layout.
    if (pathname !== "/admin/login" && !request.cookies.has(AUTH_COOKIE)) {
      return NextResponse.redirect(new URL("/admin/login", request.url));
    }
    return NextResponse.next();
  }

  // ad links: a route handler outside the language tree
  if (pathname.startsWith("/go/")) return NextResponse.next();

  if (pathname === "/") {
    const response = NextResponse.redirect(new URL(localePrefix(pickLocale(request)), request.url), 302);
    response.headers.set("Vary", "Cookie, User-Agent");
    return response;
  }

  // Ukrainian lives under /ua; the ISO code in the URL is a common typo.
  if (pathname === "/uk" || pathname.startsWith("/uk/")) {
    const url = request.nextUrl.clone();
    url.pathname = `/ua${pathname.slice(3)}`;
    return NextResponse.redirect(url, 301);
  }

  const gone = await goneResponse(pathname);
  if (gone) return gone;

  return intl(request);
}

export const config = {
  // Everything except the API (ours and the site's own route handlers), Next internals and files.
  matcher: ["/((?!v1|api|_next|_vercel|.*\\..*).*)"],
};
