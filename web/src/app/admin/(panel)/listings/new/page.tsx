import Link from "next/link";

import { adminT } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";
import type { AdminSection } from "@/lib/types";

import { ListingForm } from "../ListingForm";

export default async function NewListingPage() {
  const t = await adminT("listings");
  const sections = await adminFetch<AdminSection[]>("/admin/taxonomy");

  return (
    <>
      <nav className="breadcrumbs">
        <Link href="/admin/listings">{t("list.title")}</Link>
        <span aria-hidden>›</span>
        <span>{t("edit.breadcrumbNew")}</span>
      </nav>
      <h1>{t("list.new")}</h1>
      <ListingForm sections={sections} />
    </>
  );
}
