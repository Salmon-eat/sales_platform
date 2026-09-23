import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const dev = process.env.NODE_ENV !== "production";

// Google sign-in, Telegram sign-in and Cloudflare Turnstile (anti-bot check on forms): the only third
// parties. Telegram serves the button script from telegram.org and opens the login in a frame/window
// on oauth.telegram.org.
const GOOGLE = "https://accounts.google.com";
const TURNSTILE = "https://challenges.cloudflare.com";
const TELEGRAM = "https://telegram.org";
const TELEGRAM_OAUTH = "https://oauth.telegram.org";

/** What the browser may load and run. Blocks injected scripts from other sites, framing (clickjacking),
 * plugins, <base> hijacking and forms posting elsewhere. Inline scripts stay allowed: Next.js needs them
 * on static pages; every piece of user text is escaped by React. */
const CSP = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${GOOGLE}/gsi/client ${TELEGRAM} ${TURNSTILE}${dev ? " 'unsafe-eval'" : ""}`,
  `style-src 'self' 'unsafe-inline' ${GOOGLE}/gsi/style`,
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  `connect-src 'self' ${GOOGLE}/gsi/${dev ? " ws: wss:" : ""}`,
  `frame-src ${GOOGLE} ${TELEGRAM_OAUTH} ${TURNSTILE}`,
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  // no upgrade-insecure-requests: HSTS already keeps the domain on HTTPS, and the directive would break
  // the plain-HTTP preview by IP (every stylesheet and script would be asked for over https)
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // the Google sign-in popup needs to talk back to the opener
  { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [
      { source: "/:path*", headers: SECURITY_HEADERS },
      // the admin never goes into a shared or browser cache
      { source: "/admin/:path*", headers: [{ key: "Cache-Control", value: "no-store" }, { key: "X-Robots-Tag", value: "noindex, nofollow" }] },
    ];
  },
  // In production Caddy routes /v1/* to FastAPI before it reaches Next.js;
  // this rewrite makes the same relative URLs work in local dev without Caddy.
  async rewrites() {
    return [
      { source: "/v1/:path*", destination: `${apiUrl}/v1/:path*` },
      // photos of ads: Caddy serves them from disk in production, the API does it in local dev
      { source: "/media/:path*", destination: `${apiUrl}/media/:path*` },
    ];
  },
};

export default withNextIntl(nextConfig);
