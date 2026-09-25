/**
 * Admin UI texts in 4 languages, one file per screen: messages/admin/<locale>/<namespace>.json.
 * uk is the reference (npm run check:messages compares the other languages with it).
 * Loaded by src/i18n/request.ts under the "admin" key; the public site never ships them.
 */
import type { Locale } from "@/i18n/routing";

import type applications from "./uk/applications.json";
import type common from "./uk/common.json";
import type dashboard from "./uk/dashboard.json";
import type errors from "./uk/errors.json";
import type links from "./uk/links.json";
import type listings from "./uk/listings.json";
import type login from "./uk/login.json";
import type moderation from "./uk/moderation.json";
import type reportsMessages from "./uk/reports.json";
import type shell from "./uk/shell.json";
import type users from "./uk/users.json";

export const ADMIN_NAMESPACES = [
  "common",
  "shell",
  "login",
  "errors",
  "users",
  "listings",
  "moderation",
  "reports",
  "applications",
  "dashboard",
  "links",
] as const;

export type AdminMessages = {
  common: typeof common;
  shell: typeof shell;
  login: typeof login;
  errors: typeof errors;
  users: typeof users;
  listings: typeof listings;
  moderation: typeof moderation;
  reports: typeof reportsMessages;
  applications: typeof applications;
  dashboard: typeof dashboard;
  links: typeof links;
};

export async function loadAdminMessages(locale: Locale): Promise<AdminMessages> {
  const entries = await Promise.all(
    ADMIN_NAMESPACES.map(async (ns) => [ns, (await import(`./${locale}/${ns}.json`)).default] as const),
  );
  return Object.fromEntries(entries) as AdminMessages;
}
