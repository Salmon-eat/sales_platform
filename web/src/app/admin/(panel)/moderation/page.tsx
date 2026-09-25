import { AlertTriangle } from "lucide-react";

import { adminT, getAdminLocale } from "@/lib/admin-locale";
import { adminFetch } from "@/lib/auth";

import { approveCompany, rejectCompany } from "../../companies-actions";
import { approveAd, rejectAd } from "../../moderation-actions";

type CompanyInQueue = {
  id: number;
  name: string;
  about: string;
  lang: string;
  city_name: string | null;
  categories: string[];
  logo: string | null;
  owner_name: string | null;
  address: string | null;
  hours: string | null;
  phone: string | null;
  email: string | null;
  site: string | null;
  updated_at: string;
};

type QueueItem = {
  id: number;
  title: string;
  description: string;
  lang: string;
  section_name: string;
  category_name: string;
  location_name: string | null;
  price: number | null;
  price_period: string | null;
  price_kind: string;
  attributes: Record<string, unknown>;
  contact: Record<string, string>;
  photos: string[];
  flags: string[];
  author_name: string | null;
  author_email: string | null;
  author_ads: number;
  created_at: string;
  updated_at: string;
};

type Page = { items: QueueItem[]; total: number; page: number; per_page: number };

const REASONS = [
  "wrong_category",
  "contacts_in_text",
  "bad_photos",
  "duplicate",
  "prohibited",
  "spam",
  "unclear",
  "other",
] as const;

/** A flag from the automatic check -> the word shown to the moderator. */
function flagKey(flag: string): string {
  return flag.startsWith("stop_word:") ? `flag_stop_${flag.slice("stop_word:".length)}` : `flag_${flag}`;
}

/** Pre-moderation: nothing a visitor writes appears on the site before someone here has read it. */
export default async function ModerationPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; error?: string }>;
}) {
  const { ok } = await searchParams;
  const t = await adminT("moderation");
  const locale = await getAdminLocale();
  const [queue, firms] = await Promise.all([
    adminFetch<Page>("/admin/moderation/queue"),
    adminFetch<CompanyInQueue[]>("/admin/companies/queue").catch(() => []),
  ]);
  const when = new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Madrid",
  });
  const euro = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

  const price = (item: QueueItem) =>
    item.price_kind === "free"
      ? t("free")
      : item.price !== null
        ? `${euro.format(item.price)}${item.price_period ? ` / ${item.price_period}` : ""}`
        : item.price_kind === "negotiable"
          ? t("negotiable")
          : t("noPrice");

  return (
    <section className="admin-section">
      <header className="admin-head">
        <div>
          <h1>{t("title")}</h1>
          <p className="muted">{t("subtitle")}</p>
        </div>
        <span className="admin-count">{t("waiting", { count: queue.total })}</span>
      </header>

      {ok && <p className="notice notice--ok">{t("sent")}</p>}

      {firms.length > 0 && (
        <>
          <h2 className="admin-subhead">{t("firmsTitle", { count: firms.length })}</h2>
          <ul className="mod-list">
            {firms.map((firm) => (
              <li key={firm.id} className="mod-card">
                <div className="mod-card__text">
                  <div className="mod-card__top">
                    <span className="badge">{t("firm")}</span>
                    <span className="muted small">
                      #{firm.id} · {firm.owner_name} · {when.format(new Date(firm.updated_at))}
                    </span>
                  </div>
                  <h2 lang={firm.lang}>{firm.name}</h2>
                  <p className="mod-card__body" lang={firm.lang}>
                    {firm.about}
                  </p>
                  <dl className="mod-card__meta">
                    <div>
                      <dt>{t("firmServices")}</dt>
                      <dd>{firm.categories.join(" · ") || "—"}</dd>
                    </div>
                    <div>
                      <dt>{t("firmWhere")}</dt>
                      <dd>{[firm.city_name, firm.address, firm.hours].filter(Boolean).join(" · ") || "—"}</dd>
                    </div>
                    <div>
                      <dt>{t("contact")}</dt>
                      <dd>{[firm.phone, firm.email, firm.site].filter(Boolean).join(" · ") || "—"}</dd>
                    </div>
                  </dl>
                </div>
                <div className="mod-card__side">
                  {firm.logo && (
                    <ul className="mod-card__photos">
                      <li>
                        <img src={firm.logo} alt="" />
                      </li>
                    </ul>
                  )}
                  <form action={approveCompany}>
                    <input type="hidden" name="id" value={firm.id} />
                    <label className="check">
                      <input type="checkbox" name="verified" />
                      <span>{t("firmVerified")}</span>
                    </label>
                    <button type="submit" className="btn btn--primary btn--block">
                      {t("approve")}
                    </button>
                  </form>
                  <form action={rejectCompany} className="mod-card__reject">
                    <input type="hidden" name="id" value={firm.id} />
                    <label className="field">
                      <span>{t("rejectWhy")}</span>
                      <select name="reason" defaultValue="unclear">
                        {REASONS.map((reason) => (
                          <option key={reason} value={reason}>
                            {t(`reason_${reason}` as "reason_other")}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>{t("rejectNote")}</span>
                      <input name="note" maxLength={500} />
                    </label>
                    <button type="submit" className="btn btn--ghost-dark btn--block">
                      {t("reject")}
                    </button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
          <h2 className="admin-subhead">{t("adsTitle")}</h2>
        </>
      )}

      {queue.items.length === 0 ? (
        <p className="muted">{t("empty")}</p>
      ) : (
        <ul className="mod-list">
          {queue.items.map((item) => (
            <li key={item.id} className="mod-card">
              <div className="mod-card__text">
                <div className="mod-card__top">
                  <span className="badge">{item.section_name}</span>
                  <span className="muted small">
                    #{item.id} · {item.category_name}
                    {item.location_name ? ` · ${item.location_name}` : ""} · {when.format(new Date(item.updated_at))}
                  </span>
                </div>
                <h2 lang={item.lang}>{item.title}</h2>
                <p className="mod-card__price">{price(item)}</p>
                <p className="mod-card__body" lang={item.lang}>
                  {item.description}
                </p>

                {item.flags.length > 0 && (
                  <p className="mod-card__flags">
                    <AlertTriangle size={14} aria-hidden /> <strong>{t("flags")}:</strong>{" "}
                    {item.flags.map((flag) => t(flagKey(flag) as "flag_contact_in_text")).join(", ")}
                  </p>
                )}

                <dl className="mod-card__meta">
                  <div>
                    <dt>{t("author")}</dt>
                    <dd>
                      {item.author_name ?? "—"} {item.author_email ? `<${item.author_email}>` : ""} ·{" "}
                      {t("authorAds", { count: item.author_ads })}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("contact")}</dt>
                    <dd>{Object.values(item.contact).filter(Boolean).join(" · ") || "—"}</dd>
                  </div>
                  {Object.keys(item.attributes).length > 0 && (
                    <div>
                      <dt>·</dt>
                      <dd>
                        {Object.entries(item.attributes)
                          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
                          .join(" · ")}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>

              <div className="mod-card__side">
                {item.photos.length > 0 && (
                  <ul className="mod-card__photos">
                    {item.photos.map((photo) => (
                      <li key={photo}>
                        <img src={photo} alt="" />
                      </li>
                    ))}
                  </ul>
                )}
                <form action={approveAd}>
                  <input type="hidden" name="id" value={item.id} />
                  <button type="submit" className="btn btn--primary btn--block">
                    {t("approve")}
                  </button>
                </form>
                <form action={rejectAd} className="mod-card__reject">
                  <input type="hidden" name="id" value={item.id} />
                  <label className="field">
                    <span>{t("rejectWhy")}</span>
                    <select name="reason" defaultValue="wrong_category">
                      {REASONS.map((reason) => (
                        <option key={reason} value={reason}>
                          {t(`reason_${reason}` as "reason_other")}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>{t("rejectNote")}</span>
                    <input name="note" maxLength={500} />
                  </label>
                  <button type="submit" className="btn btn--ghost-dark btn--block">
                    {t("reject")}
                  </button>
                </form>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
