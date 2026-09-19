// Shared by proxy.ts (edge of the request) and server code. The cookie holds the session token; the
// Next.js server sends it to the API as `Authorization: Bearer` (the API never reads cookies).
export const AUTH_COOKIE = "access_token";
export const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // admin spec §1: 30-day sessions
