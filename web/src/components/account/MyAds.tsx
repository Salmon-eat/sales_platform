import { Camera, Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import { accountFetch } from "@/lib/account";
import { formatEuro } from "@/lib/listing-format";
import { localizedPath, prefixed } from "@/lib/routes";
import type { MyListing } from "@/lib/types";

import { getPrices } from "@/app/[locale]/order-actions";

import { MyAdActions } from "./MyAdActions";
import { PromoteButtons } from "./PromoteButtons";

/** "My ads": what I posted, where each one stands, and what I can do with it. */
export async function MyAds({ locale }: { locale: Locale }) {
  const t = await getTranslations("myAds");
  const [ads, prices] = await Promise.all([
    accountFetch<MyListing[]>(`/my/listings?lang=${locale}`)
      .then((rows) => rows ?? [])
      .catch(() => []),
    getPrices(),
  ]);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Europe/Madrid" });

  return (
    <section className="my-ads">
      <div className="home-block__head">
        <h2>{t("tab")}</h2>
        <Link href={localizedPath(locale, { type: "static", key: "publish" })} className="btn btn--primary btn--sm">
          <Plus size={15} aria-hidden /> {t("post")}
        </Link>
      </div>

      {ads.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <ul className="my-ad-list">
          {ads.map((ad) => (
            <li key={ad.id} className="my-ad">
              <div className="my-ad__photo">
                {ad.photo ? <img src={ad.photo} alt="" /> : <Camera size={18} aria-hidden />}
              </div>
              <div className="my-ad__body">
                <div className="my-ad__top">
                  <span className={`badge badge--${ad.status}`}>{t(`status_${ad.status}`)}</span>
                  {ad.status === "active" && ad.expires_at && (
                    <span className="muted small">{t("until", { date: date.format(new Date(ad.expires_at)) })}</span>
                  )}
                </div>
                <h3>
                  {ad.path ? (
                    <Link href={prefixed(locale, ad.path)} className="listing-link">
                      {ad.title}
                    </Link>
                  ) : (
                    ad.title
                  )}
                </h3>
                <p className="my-ad__meta muted small">
                  {[
                    ad.category_name,
                    ad.location_name,
                    ad.price !== null ? formatEuro(ad.price, locale) : null,
                    ad.photos_count ? t("photosCount", { count: ad.photos_count }) : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                {ad.status === "rejected" && ad.reject_reason && (
                  <p className="my-ad__rejected">
                    <strong>{t("rejected")}:</strong> {t(`reason_${ad.reject_reason}` as "reason_other")}
                    {ad.reject_note ? ` — ${ad.reject_note}` : ""}
                  </p>
                )}
                <div className="my-ad__actions">
                  <Link
                    href={`${localizedPath(locale, { type: "static", key: "publish" })}?edit=${ad.id}`}
                    className="btn btn--outline btn--sm"
                  >
                    {t("edit")}
                  </Link>
                  <MyAdActions id={ad.id} status={ad.status} />
                </div>
                {/* extras only make sense for an ad people can actually see */}
                {ad.status === "active" && <PromoteButtons listingId={ad.id} products={prices.products} />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
