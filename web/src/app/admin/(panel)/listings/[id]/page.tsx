import Link from "next/link";
import { notFound } from "next/navigation";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { ApiError } from "@/lib/api";
import { adminFetch } from "@/lib/auth";
import type { AdminListingDetail, AdminSection } from "@/lib/types";

import { runListingAction } from "../../../listing-actions";
import { ListingForm } from "../ListingForm";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ error?: string; created?: string }>;
};

export default async function EditListingPage({ params, searchParams }: Props) {
  const { id } = await params;
  const flash = await searchParams;
  if (!/^\d+$/.test(id)) notFound();

  const t = await adminT("listings");
  const locale = await getAdminLocale();
  const dateTime = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Madrid" });
  const fmt = (iso: string | null) => (iso ? dateTime.format(new Date(iso)) : "—");

  let listing: AdminListingDetail;
  try {
    listing = await adminFetch<AdminListingDetail>(`/admin/listings/${id}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  const sections = await adminFetch<AdminSection[]>("/admin/taxonomy");
  const s = listing.status;
  const byLang = (lang: string) => listing.translations.find((tr) => tr.lang === lang)?.title;
  const title = byLang(locale) ?? byLang(listing.original_lang) ?? listing.translations[0]?.title;

  type Action = "publish" | "pause" | "resume" | "extend" | "close" | "delete";
  const actions: [Action, string][] = [];
  if (listing.can_edit) {
    if (s === "draft") actions.push(["publish", "btn--primary"]);
    if (s === "active") actions.push(["pause", "btn--ghost-dark"]);
    if (s === "paused") actions.push(["resume", "btn--primary"]);
    if (["active", "paused", "expired"].includes(s)) actions.push(["extend", "btn--ghost-dark"]);
    if (["active", "paused", "expired"].includes(s)) actions.push(["close", "btn--ghost-dark"]);
    if (s === "draft") actions.push(["delete", "btn--danger"]);
  }

  return (
    <>
      <nav className="breadcrumbs">
        <Link href="/admin/listings">{t("list.title")}</Link>
        <span aria-hidden>›</span>
        <span>№{listing.id}</span>
      </nav>
      <div className="admin-head">
        <h1>{title}</h1>
        <span className={`status status--${s}`}>{t(`status.${s}`)}</span>
      </div>

      {flash.created && <p className="notice notice--ok">{t("edit.created")}</p>}
      {flash.error && <p className="notice notice--error">{flash.error}</p>}
      {!listing.can_edit && <p className="notice">{t("edit.readOnly", { email: listing.created_by_email ?? "—" })}</p>}

      <div className="listing-status-bar">
        <dl>
          <div>
            <dt>{t("edit.publishedAt")}</dt>
            <dd>{fmt(listing.published_at)}</dd>
          </div>
          <div>
            <dt>{t("edit.expiresAt")}</dt>
            <dd>{fmt(listing.expires_at)}</dd>
          </div>
          {listing.closed_at && (
            <div>
              <dt>{t("edit.closedAt")}</dt>
              <dd>{fmt(listing.closed_at)}</dd>
            </div>
          )}
          <div>
            <dt>{t("edit.author")}</dt>
            <dd>{listing.created_by_email ?? "—"}</dd>
          </div>
        </dl>
        <form action={runListingAction} className="inline-form">
          <input type="hidden" name="id" value={listing.id} />
          {actions.map(([action, variant]) => (
            <button key={action} name="action" value={action} className={`btn btn--sm ${variant}`}>
              {t(`actions.${action}`)}
            </button>
          ))}
        </form>
      </div>

      <ListingForm sections={sections} listing={listing} readOnly={!listing.can_edit} />
    </>
  );
}
