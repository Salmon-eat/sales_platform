import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch, requireAdminPage } from "@/lib/auth";
import type { AdminUser } from "@/lib/types";

import { addUser, signOutUser, updateUser } from "../../users-actions";

type Props = { searchParams: Promise<{ error?: string; ok?: string; email?: string }> };

const ERRORS = ["email_exists", "cannot_change_self", "email"] as const;

/** Staff whitelist (admin spec §1): only these emails can sign in with Google. */
export default async function UsersPage({ searchParams }: Props) {
  const me = await requireAdminPage();
  const { error, ok, email } = await searchParams;
  const users = await adminFetch<AdminUser[]>("/admin/users");
  const t = await adminT("users");
  const tc = await adminT("common");
  const dateTime = new Intl.DateTimeFormat(await getAdminLocale(), {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });
  const errorText = ERRORS.find((e) => e === error);
  const roles = ["manager", "admin"] as const;

  return (
    <>
      <h1>{t("title")}</h1>
      <p className="muted">{t("intro")}</p>
      {error && <p className="notice notice--error">{errorText ? t(`error_${errorText}`) : tc("notSaved")}</p>}
      {ok === "added" && <p className="notice notice--ok">{t("added", { email: email ?? "" })}</p>}
      {ok === "closed" && <p className="notice notice--ok">{t("closed")}</p>}

      <form action={addUser} className="panel admin-add-user">
        <legend>{t("addTitle")}</legend>
        <div className="field-row">
          <label className="field">
            <span>{t("email")}</span>
            <input name="email" type="email" required placeholder="name@gmail.com" />
          </label>
          <label className="field">
            <span>{t("name")}</span>
            <input name="name" maxLength={200} />
          </label>
          <label className="field">
            <span>{t("role")}</span>
            <select name="role" defaultValue="manager">
              {roles.map((role) => (
                <option key={role} value={role}>
                  {tc(`role_${role}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div>
          <button type="submit" className="btn btn--primary">
            {tc("add")}
          </button>
        </div>
      </form>

      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("person")}</th>
              <th>{t("role")}</th>
              <th>{t("access")}</th>
              <th>{t("lastLogin")}</th>
              <th className="num">{t("sessions")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const self = user.id === me.id;
              return (
                <tr key={user.id} className={user.is_active ? undefined : "row--muted"}>
                  <td>
                    <strong>{user.name ?? "—"}</strong>
                    {self && <span className="muted"> {t("you")}</span>}
                    <div className="small muted">{user.email}</div>
                  </td>
                  <td>
                    {self ? (
                      tc(`role_${user.role}`)
                    ) : (
                      <form action={updateUser} className="inline-form">
                        <input type="hidden" name="id" value={user.id} />
                        <select name="role" defaultValue={user.role} aria-label={t("role")}>
                          {roles.map((role) => (
                            <option key={role} value={role}>
                              {tc(`role_${role}`)}
                            </option>
                          ))}
                        </select>
                        <button type="submit" className="btn btn--ghost-dark btn--sm">
                          {tc("save")}
                        </button>
                      </form>
                    )}
                  </td>
                  <td>
                    {self ? (
                      <span className="status status--active">{t("on")}</span>
                    ) : (
                      <form action={updateUser}>
                        <input type="hidden" name="id" value={user.id} />
                        <input type="hidden" name="is_active" value={user.is_active ? "false" : "true"} />
                        <button
                          type="submit"
                          className={`switch ${user.is_active ? "switch--on" : ""}`}
                          role="switch"
                          aria-checked={user.is_active}
                          aria-label={user.is_active ? t("turnOff") : t("turnOn")}
                        >
                          <span>{user.is_active ? t("on") : t("off")}</span>
                        </button>
                      </form>
                    )}
                  </td>
                  <td className="small">{user.last_login_at ? dateTime.format(new Date(user.last_login_at)) : t("never")}</td>
                  <td className="num">{user.active_sessions}</td>
                  <td>
                    {user.active_sessions > 0 && (
                      <form action={signOutUser}>
                        <input type="hidden" name="id" value={user.id} />
                        <button type="submit" className="btn btn--ghost-dark btn--sm">
                          {t("closeSessions")}
                        </button>
                      </form>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
