"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

type Key = "dashboard" | "applications" | "moderation" | "listings" | "links" | "users";
type Item = { href: string; label: Key; also?: string[] };

// admin spec §2: admin-only items go at the bottom and are hidden from managers.
// Candidates, employers and content are added here together with their screens.
const STAFF: Item[] = [
  { href: "/admin", label: "dashboard" },
  { href: "/admin/applications", label: "applications" },
  { href: "/admin/moderation", label: "moderation" },
  { href: "/admin/listings", label: "listings" },
  { href: "/admin/links", label: "links" },
];
const ADMIN: Item[] = [
  { href: "/admin/users", label: "users" },
];

export function AdminNav({ isAdmin }: { isAdmin: boolean }) {
  const t = useTranslations("admin.shell");
  const pathname = usePathname();
  const active = (item: Item) =>
    [item.href, ...(item.also ?? [])].some((href) => (href === "/admin" ? pathname === href : pathname.startsWith(href)));

  const render = (item: Item) => (
    <Link
      key={item.href}
      href={item.href}
      className={active(item) ? "admin-nav-item admin-nav-item--active" : "admin-nav-item"}
      aria-current={active(item) ? "page" : undefined}
    >
      {t(item.label)}
    </Link>
  );

  return (
    <nav className="admin-nav" aria-label={t("nav")}>
      {STAFF.map(render)}
      {isAdmin && ADMIN.map(render)}
    </nav>
  );
}
