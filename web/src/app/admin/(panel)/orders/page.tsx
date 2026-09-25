import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";

import { cancelOrder, markOrderPaid } from "../../orders-actions";

type Order = {
  id: number;
  product: string;
  days: number;
  amount: number;
  currency: string;
  status: string;
  provider: string;
  listing_id: number | null;
  company_id: number | null;
  buyer: string | null;
  note: string | null;
  created_at: string;
  paid_at: string | null;
};

/** What people bought. Until the card account exists, a transfer is confirmed here by hand. */
export default async function OrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; error?: string }>;
}) {
  const { ok, error } = await searchParams;
  const t = await adminT("orders");
  const locale = await getAdminLocale();
  const orders = await adminFetch<Order[]>("/admin/orders");
  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" });
  const when = new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });
  const waiting = orders.filter((order) => order.status === "new");
  const paid = orders.filter((order) => order.status === "paid");
  const earned = paid.reduce((sum, order) => sum + order.amount, 0);

  return (
    <section className="admin-section">
      <header className="admin-head">
        <div>
          <h1>{t("title")}</h1>
          <p className="muted">{t("subtitle")}</p>
        </div>
        <span className="admin-count">
          {t("waiting", { count: waiting.length })} · {t("earned", { sum: money.format(earned / 100) })}
        </span>
      </header>

      {ok && <p className="notice notice--ok">{t("done")}</p>}
      {error && <p className="notice notice--error">{t("failed")}</p>}

      {orders.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("what")}</th>
              <th>{t("who")}</th>
              <th>{t("amount")}</th>
              <th>{t("status")}</th>
              <th>{t("when")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>
                  {t(`product_${order.product}` as "product_bump")}
                  <div className="muted small">
                    {order.listing_id ? `#${order.listing_id}` : ""}
                    {order.company_id ? `${t("company")} #${order.company_id}` : ""}
                    {order.days ? ` · ${t("days", { count: order.days })}` : ""}
                  </div>
                </td>
                <td>{order.buyer ?? "—"}</td>
                <td>{money.format(order.amount / 100)}</td>
                <td>
                  <span className={`badge badge--${order.status === "paid" ? "active" : "pending"}`}>
                    {t(`status_${order.status}` as "status_new")}
                  </span>
                  <div className="muted small">
                    {t(`provider_${order.provider}` as "provider_card")}
                    {order.note ? ` · ${order.note}` : ""}
                  </div>
                </td>
                <td className="muted small">
                  {when.format(new Date(order.created_at))}
                  {order.paid_at && <div>{t("paidAt", { date: when.format(new Date(order.paid_at)) })}</div>}
                </td>
                <td>
                  {order.status === "new" && (
                    <div className="admin-row-actions">
                      <form action={markOrderPaid}>
                        <input type="hidden" name="id" value={order.id} />
                        <input name="note" maxLength={200} placeholder={t("notePlaceholder")} />
                        <button type="submit" className="btn btn--primary btn--sm">
                          {t("markPaid")}
                        </button>
                      </form>
                      <form action={cancelOrder}>
                        <input type="hidden" name="id" value={order.id} />
                        <button type="submit" className="link-button">
                          {t("cancel")}
                        </button>
                      </form>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
