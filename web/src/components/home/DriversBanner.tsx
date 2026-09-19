import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n/routing";
import { localizedPath } from "@/lib/routes";

export async function DriversBanner({ locale }: { locale: Locale }) {
  const t = await getTranslations("home");

  return (
    <section className="drivers-banner">
      <div>
        <span className="badge">{t("driversBadge")}</span>
        <h2>{t("driversTitle")}</h2>
        <p>{t("driversText")}</p>
      </div>
      <Link href={localizedPath(locale, { type: "agency", key: "drivers" })} className="btn btn--outline-light btn--lg">
        {t("go")}
        <ArrowRight size={16} aria-hidden />
      </Link>
    </section>
  );
}
