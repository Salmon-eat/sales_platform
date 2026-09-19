/**
 * Own anonymous analytics: random ids in the browser, no cookies, no IP or personal data.
 * Events go to /v1/events with sendBeacon, so leaving the page does not lose them.
 *
 * Attribution: utm_* from the URL (ad links /go/<code> add them), else the referring site
 * (google, instagram…); kept 30 days so a person who comes back later and applies is still
 * counted for the blogger who brought them.
 */

export type TrackType = "page_view" | "page_leave" | "listing_view" | "apply_open" | "apply_sent" | "search" | "contact_click";

type Attribution = { source: string; campaign: string | null; at: number };
type TrackOptions = { listing_id?: number; duration_ms?: number; props?: Record<string, string | number | boolean> };

const VISITOR_KEY = "bz_v";
const SESSION_KEY = "bz_s";
const ATTR_KEY = "bz_attr";
const SESSION_IDLE_MS = 30 * 60 * 1000;
const ATTRIBUTION_MS = 30 * 24 * 60 * 60 * 1000;

const SOURCES: [RegExp, string][] = [
  [/(^|\.)google\./, "google"],
  [/(^|\.)bing\.com$/, "bing"],
  [/(^|\.)(yandex\.|ya\.ru)/, "yandex"],
  [/(^|\.)duckduckgo\.com$/, "duckduckgo"],
  [/(^|\.)instagram\.com$/, "instagram"],
  [/(^|\.)(facebook\.com|fb\.com|fb\.me)$/, "facebook"],
  [/(^|\.)(t\.me|telegram\.org|telegram\.me)$/, "telegram"],
  [/(^|\.)tiktok\.com$/, "tiktok"],
  [/(^|\.)(youtube\.com|youtu\.be)$/, "youtube"],
  [/(^|\.)(whatsapp\.com|wa\.me)$/, "whatsapp"],
  [/(^|\.)viber\.com$/, "viber"],
];

function randomId(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function read<T>(storage: Storage, key: string): T | null {
  try {
    const raw = storage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(storage: Storage, key: string, value: unknown): void {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    // private mode or full storage: analytics is best effort
  }
}

function visitorId(): string {
  const stored = read<string>(localStorage, VISITOR_KEY);
  if (stored) return stored;
  const id = randomId();
  write(localStorage, VISITOR_KEY, id);
  return id;
}

/** A visit ends after 30 idle minutes, like in common analytics tools. */
function sessionId(): { id: string; isNew: boolean } {
  const now = Date.now();
  const stored = read<{ id: string; last: number }>(sessionStorage, SESSION_KEY);
  const isNew = !stored || now - stored.last > SESSION_IDLE_MS;
  const id = isNew ? randomId() : stored.id;
  write(sessionStorage, SESSION_KEY, { id, last: now });
  return { id, isNew };
}

function sourceFromReferrer(): string | null {
  if (!document.referrer) return null;
  try {
    const host = new URL(document.referrer).hostname.replace(/^www\./, "");
    if (host === location.hostname) return null;
    return SOURCES.find(([re]) => re.test(host))?.[1] ?? host;
  } catch {
    return null;
  }
}

function attribution(isNewSession: boolean): Attribution {
  const params = new URLSearchParams(location.search);
  const utmSource = params.get("utm_source");
  const stored = read<Attribution>(localStorage, ATTR_KEY);
  const fresh = stored && Date.now() - stored.at < ATTRIBUTION_MS ? stored : null;

  let next: Attribution | null = null;
  if (utmSource) {
    next = { source: utmSource.toLowerCase(), campaign: params.get("utm_campaign")?.toLowerCase() ?? null, at: Date.now() };
  } else if (isNewSession) {
    const ref = sourceFromReferrer();
    // a direct visit keeps the earlier blogger/ad; another site replaces it
    if (ref) next = { source: ref, campaign: null, at: Date.now() };
  }
  if (next) {
    write(localStorage, ATTR_KEY, next);
    return next;
  }
  return fresh ?? { source: "direct", campaign: null, at: Date.now() };
}

let current: Attribution | null = null;

/** utm for the application form: the manager sees where the person came from. */
export function attributionUtm(): Record<string, string> {
  const a = current ?? read<Attribution>(localStorage, ATTR_KEY);
  if (!a || a.source === "direct") return {};
  return { utm_source: a.source, ...(a.campaign ? { utm_campaign: a.campaign } : {}) };
}

const recent = new Map<string, number>();

export function track(type: TrackType, { path, ...options }: TrackOptions & { path?: string } = {}): void {
  if (typeof window === "undefined") return;
  const page = path ?? location.pathname;
  // the same view twice within a second (double effects in dev, quick re-render) counts once
  const key = `${type}|${page}|${options.listing_id ?? ""}`;
  const now = Date.now();
  if (type !== "page_leave" && now - (recent.get(key) ?? 0) < 1000) return;
  recent.set(key, now);
  try {
    const session = sessionId();
    if (!current || session.isNew || type === "page_view") current = attribution(session.isNew);
    const width = window.innerWidth;
    const body = JSON.stringify({
      visitor: visitorId(),
      session: session.id,
      lang: document.documentElement.lang || null,
      source: current.source.slice(0, 40),
      campaign: current.campaign?.slice(0, 60) ?? null,
      mobile: width < 768,
      tablet: width >= 768 && width < 1100 && navigator.maxTouchPoints > 0,
      events: [{ type, path: page, ...options }],
    });
    const blob = new Blob([body], { type: "application/json" });
    if (!navigator.sendBeacon?.("/v1/events", blob)) {
      void fetch("/v1/events", { method: "POST", body, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(
        () => undefined,
      );
    }
  } catch {
    // never break the page because of analytics
  }
}
