import { getTranslations } from "next-intl/server";

import { myOrders } from "@/app/[locale]/order-actions";
import type { Locale } from "@/i18n/routing";

/** What I bought and whether it has been paid for; a receipt outlives the ad it paid for. */
export async function Orders({ locale }: { locale: Locale }) {
  const t = await getTranslations("promote");
  const orders = await myOrders();
  if (orders.length === 0) return null;

  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" });
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Europe/Madrid" });

  return (
    <section className="orders">
      <div className="home-block__head">
        <h2>{t("ordersTitle")}</h2>
      </div>
      <ul className="order-list">
        {orders.map((order) => (
          <li key={order.id} className="order-row">
            <span>{t(order.product as "bump")}</span>
            <span className="muted small">
              {order.listing_id ? `#${order.listing_id}` : ""} · {date.format(new Date(order.created_at))}
            </span>
            <strong>{money.format(order.amount / 100)}</strong>
            <span className={`badge badge--${order.status === "paid" ? "active" : "pending"}`}>
              {t(`status_${order.status}` as "status_new")}
            </span>
          </li>
        ))}
      </ul>
      <p className="muted small">{t("howToPay")}</p>
    </section>
  );
}
