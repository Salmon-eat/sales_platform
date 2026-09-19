import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import { asLocale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";

export default function NotFound() {
  const t = useTranslations("notFound");
  const locale = asLocale(useLocale());

  return (
    <div className="container page">
      <h1>{t("title")}</h1>
      <Link href={localizedPath(locale, { type: "home" })} className="btn btn--primary btn--lg">
        {t("back")}
      </Link>
    </div>
  );
}
