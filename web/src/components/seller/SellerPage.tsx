import { Star } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AdCard } from "@/components/home/AdCard";
import { ReviewForm } from "@/components/seller/ReviewForm";
import type { Locale } from "@/i18n/routing";
import { getAccount } from "@/lib/account";
import { ApiError, apiFetch } from "@/lib/api";
import type { ListingCard, SellerPageData } from "@/lib/types";

async function load(id: number, locale: Locale): Promise<SellerPageData> {
  try {
    return await apiFetch<SellerPageData>(`/sellers/${id}?lang=${locale}`, { revalidate: 60 });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function sellerMetadata(locale: Locale, id: number): Promise<Metadata> {
  const seller = await load(id, locale);
  return { title: seller.name, robots: { index: false, follow: true } };
}

/** Stars as a picture plus the number in words, so it reads the same to a screen reader. */
function Stars({ rating }: { rating: number }) {
  return (
    <span className="stars" aria-hidden>
      {[1, 2, 3, 4, 5].map((star) => (
        <Star key={star} size={15} className={star <= Math.round(rating) ? "star star--on" : "star"} />
      ))}
    </span>
  );
}

/** Everything a buyer wants to know before writing to a stranger: their rating and what they sell. */
export async function SellerPage({ locale, id }: { locale: Locale; id: number }) {
  const t = await getTranslations("seller");
  const seller = await load(id, locale);
  const account = await getAccount();
  const date = new Intl.DateTimeFormat(locale, { year: "numeric", month: "long", timeZone: "Europe/Madrid" });
  const mine = account?.id === seller.id;

  return (
    <div className="container static-page">
      <section className="seller-head">
        <h1>{seller.name}</h1>
        <p className="seller-head__meta muted">
          {seller.rating !== null ? (
            <>
              <Stars rating={seller.rating} />
              <strong>{seller.rating.toFixed(1)}</strong>
              <span>{t("reviewsCount", { count: seller.reviews_count })}</span>
            </>
          ) : (
            <span>{t("noReviews")}</span>
          )}
          <span>· {t("since", { date: date.format(new Date(seller.since)) })}</span>
        </p>
      </section>

      {seller.listings.length > 0 && (
        <section className="home-block">
          <div className="home-block__head">
            <h2>{t("theirAds")}</h2>
          </div>
          <ul className="ad-grid">
            {seller.listings.map((item: ListingCard) => (
              <li key={item.id}>
                <AdCard listing={item} locale={locale} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="home-block">
        <div className="home-block__head">
          <h2>{t("reviews")}</h2>
        </div>
        {seller.reviews.length === 0 ? (
          <p className="muted">{t("noReviewsYet")}</p>
        ) : (
          <ul className="review-list">
            {seller.reviews.map((review) => (
              <li key={review.id} className="review">
                <div className="review__head">
                  <strong>{review.author_name}</strong>
                  <Stars rating={review.rating} />
                  <span className="muted small">
                    {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
                      new Date(review.created_at),
                    )}
                  </span>
                </div>
                {review.text && <p>{review.text}</p>}
                {review.reply && (
                  <p className="review__reply">
                    <strong>{t("sellerReplied")}:</strong> {review.reply}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}

        {account && !mine && <ReviewForm sellerId={seller.id} />}
        {!account && <p className="muted small">{t("signInToReview")}</p>}
      </section>
    </div>
  );
}
