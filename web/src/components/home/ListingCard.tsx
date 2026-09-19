"use client";

import { BadgeCheck, FileCheck, Gift, House, Languages } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { FavoriteButton } from "@/components/saved/FavoriteButton";
import type { Locale } from "@/i18n/routing";
import { formatSalaryRange } from "@/lib/listing-format";
import { prefixed } from "@/lib/routes";
import { useApplied, useViewed } from "@/lib/saved";
import type { CardTag, ListingCard as Card } from "@/lib/types";

const UNIT = { month: "unitMonth", hour: "unitHour", day: "unitDay", week: "unitWeek" } as const;
/** enough to see what makes this job attractive; the rest is "+N" and on the job page */
const MAX_TAGS = 7;

type Tag = { key: string; label: string; kind: CardTag["kind"] | "housing" };
const TAG_ICONS: Partial<Record<Tag["kind"], typeof House>> = {
  housing: House,
  lang: Languages,
  doc: FileCheck,
  ok: BadgeCheck,
  perk: Gift,
};

/** "2 h ago", "yesterday"; coarse enough that server and client render the same text. */
function ago(iso: string, locale: Locale): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (minutes < 60) return rtf.format(-Math.max(minutes, 1), "minute");
  if (minutes < 60 * 24) return rtf.format(-Math.round(minutes / 60), "hour");
  return rtf.format(-Math.round(minutes / (60 * 24)), "day");
}

/**
 * Listing card (spec §11): the salary is the most visible element (right on desktop, first row on
 * mobile), then the title, "company · city · time", the tags that make the job attractive, favourite and
 * the apply button.
 */
export function ListingCard({ listing, locale, note }: { listing: Card; locale: Locale; note?: string }) {
  const t = useTranslations("listing");
  const tSearch = useTranslations("search");
  const applied = Boolean(useApplied().get(listing.id));
  const viewed = useViewed().has(listing.id);
  const href = prefixed(locale, listing.path);

  const place = listing.location_scope === "spain_wide" ? t("spainWide") : listing.location?.name;
  const company = listing.source === "agency" ? t("agencyName") : listing.employer_name;
  // what catches the eye first: housing, language, papers, perks; then the schedule and the contract
  const housingCost = listing.tags?.find((tag) => tag.key === "housing_cost")?.label;
  const allTags: Tag[] = [
    listing.housing && {
      key: "housing",
      label: housingCost ? `${t("housing")} · ${housingCost.toLocaleLowerCase(locale)}` : t("housing"),
      kind: "housing",
    },
    listing.no_language && { key: "no_language", label: t("noLanguage"), kind: "info" },
    listing.no_experience && { key: "no_experience", label: t("noExperience"), kind: "info" },
    ...(listing.tags ?? []).filter((tag) => tag.key !== "housing_cost"),
    ...(listing.schedule ?? []).slice(0, 1).map((s) => ({ key: `schedule.${s}`, label: tSearch(`schedule_${s}` as "schedule_full"), kind: "info" as const })),
    listing.contract && { key: "contract", label: tSearch(`contract_${listing.contract}` as "contract_indefinido"), kind: "info" as const },
  ].filter((tag): tag is Tag => Boolean(tag));
  const tags = allTags.slice(0, MAX_TAGS);
  const more = allTags.length - tags.length;

  const salary = formatSalaryRange(listing.salary_min, listing.salary_max, locale);

  return (
    // already opened or applied: the card fades a little, like a visited link in Google results
    <article className={applied || viewed ? "job-card job-card--seen" : "job-card"}>
      <div className="job-card-salary">
        {salary ? (
          <>
            <strong>{salary}</strong>
            <small>{t(UNIT[listing.salary_period ?? "month"])}</small>
          </>
        ) : (
          <span className="job-card-nosalary">{t("salaryNone")}</span>
        )}
      </div>
      <div className="job-card-main">
        <h3 lang={listing.lang}>
          <Link href={href} className="listing-link">
            {listing.title}
          </Link>
          {listing.is_urgent && <span className="urgent-badge">{t("urgent")}</span>}
          {!listing.is_translated && <span className="lang-badge">{listing.lang === "uk" ? "UA" : listing.lang.toUpperCase()}</span>}
        </h3>
        <p className="job-card-meta">
          {viewed && !applied && <span className="job-card-viewed">{t("viewed")} · </span>}
          {[company, place].filter(Boolean).join(" · ")}
          {listing.published_at && (
            <>
              {" · "}
              <time dateTime={listing.published_at} suppressHydrationWarning>
                {ago(listing.published_at, locale)}
              </time>
            </>
          )}
        </p>
        {note && <p className="listing-note">{note}</p>}
      </div>
      <div className="job-card-foot">
        {tags.length > 0 && (
          <ul className="job-tags">
            {tags.map((tag) => {
              const Icon = TAG_ICONS[tag.kind];
              return (
                <li key={tag.key} className={`job-tag job-tag--${tag.kind}`}>
                  {Icon && <Icon size={13} aria-hidden />}
                  {tag.label}
                </li>
              );
            })}
            {more > 0 && <li className="job-tag job-tag--more">+{more}</li>}
          </ul>
        )}
        <div className="job-card-actions">
          <FavoriteButton id={listing.id} />
          {/* spec §11: after applying the button turns into an outlined "applied" state */}
          {applied ? (
            <span className="btn btn--outline btn--sm job-card-applied">{t("applied")}</span>
          ) : (
            // the job page opens at the top: title and conditions first; the form sits next to them
            // (below on phones, with an "apply" button under the title)
            <Link href={href} className="btn btn--primary btn--sm job-card-apply" tabIndex={-1}>
              {t("apply")}
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}
