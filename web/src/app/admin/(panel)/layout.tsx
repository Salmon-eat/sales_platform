import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { adminT } from "@/lib/admin-locale";
import { getCurrentUser } from "@/lib/auth";

import { logout, logoutEverywhere } from "../actions";
import { AdminLocaleSwitch } from "../AdminLocaleSwitch";
import { AdminNav } from "./AdminNav";

export default async function AdminPanelLayout({ children }: { children: ReactNode }) {
  const user = await getCurrentUser();
  if (!user || user.role === "user") redirect("/admin/login");
  const t = await adminT("shell");
  const tc = await adminT("common");

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <span className="logo logo--dark">
          bazar<span>cito</span>
        </span>
        <AdminNav isAdmin={user.role === "admin"} />
        <AdminLocaleSwitch />
        <div className="admin-user">
          {user.avatar && <img src={user.avatar} alt="" width={32} height={32} referrerPolicy="no-referrer" />}
          <div>
            <strong>{user.name ?? user.email}</strong>
            <span className="muted">{tc(`role_${user.role}`)}</span>
          </div>
        </div>
        <form action={logout}>
          <button type="submit" className="btn btn--ghost-dark btn--block">
            {t("logout")}
          </button>
        </form>
        <form action={logoutEverywhere}>
          <button type="submit" className="admin-link-button" title={t("logoutAllHint")}>
            {t("logoutAll")}
          </button>
        </form>
      </aside>
      <div className="admin-main">{children}</div>
    </div>
  );
}
