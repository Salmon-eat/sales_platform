import { LogIn } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { PageHero } from "@/components/content/PageHero";
import type { Locale } from "@/i18n/routing";
import { accountFetch, getAccount } from "@/lib/account";
import { getPopularLocations, getTaxonomy, orFallback } from "@/lib/api";
import { localizedPath } from "@/lib/routes";
import type { MyLimits, MyListingDetail, Taxonomy } from "@/lib/types";

import { PostAdForm } from "./PostAdForm";

const NO_TAXONOMY: Taxonomy = { sections: [] };
const DEFAULT_LIMITS: MyLimits = { open: 0, max_listings: 30, max_photos: 10, days: 30 };

/** "Post an ad": the form for a signed-in person, an invitation to sign in for everybody else.
 * With `editId` the same form opens an ad the person already has. */
export async function PostPage({
  locale,
  title,
  editId,
}: {
  locale: Locale;
  title: string;
  editId?: number;
}) {
  const t = await getTranslations("post");
  const crumbs = [{ name: "Citobazar", href: localizedPath(locale, { type: "home" }) }];
  const account = await getAccount();

  if (!account) {
    return (
      <>
        <PageHero crumbs={crumbs} title={title}>
          <p>{t("introText")}</p>
        </PageHero>
        <div className="container static-page static-page--narrow">
          <div className="post-signin">
            <h2>{t("signInTitle")}</h2>
            <p className="muted">{t("signInText")}</p>
            <Link
              href={localizedPath(locale, { type: "static", key: "login" })}
              className="btn btn--primary btn--lg"
            >
              <LogIn size={16} aria-hidden /> {t("signInButton")}
            </Link>
          </div>
        </div>
      </>
    );
  }

  const [taxonomy, places, limits, editing] = await Promise.all([
    orFallback(getTaxonomy(locale), NO_TAXONOMY),
    orFallback(getPopularLocations(locale, 50), []),
    accountFetch<MyLimits>("/my/limits").catch(() => null),
    editId
      ? accountFetch<MyListingDetail>(`/my/listings/${editId}?lang=${locale}`).catch(() => null)
      : null,
  ]);
  const cities = places
    .filter((place): place is typeof place & { id: number } => typeof place.id === "number")
    .sort((a, b) => a.name.localeCompare(b.name, locale));
  const rules = limits ?? DEFAULT_LIMITS;

  return (
    <>
      <PageHero crumbs={crumbs} title={title}>
        <p>{t("introText")}</p>
      </PageHero>
      <div className="container static-page">
        {!editing && rules.open >= rules.max_listings ? (
          <p className="form-error">{t("errors.too_many_listings")}</p>
        ) : (
          <PostAdForm
            taxonomy={taxonomy}
            cities={cities}
            defaults={{ name: account.name ?? "", phone: account.phone ?? "" }}
            maxPhotos={rules.max_photos}
            days={rules.days}
            initial={editing}
          />
        )}
      </div>
    </>
  );
}
