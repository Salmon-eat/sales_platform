import { getTranslations } from "next-intl/server";

import type { ApplicationOptions } from "@/lib/types";

import { ApplicationForm } from "./ApplicationForm";
import { Steps } from "./Steps";

/** "Didn't find a job? Leave a request and get a call": a block on the home page and its own page
 * (header tab), where the heading is the page's h1. */
export async function ApplicationSection({ options, asPage = false }: { options: ApplicationOptions; asPage?: boolean }) {
  const t = await getTranslations("apply");
  const Heading = asPage ? "h1" : "h2";

  return (
    <section className="apply" id="apply">
      <div className="apply-intro">
        <span className="badge">{t("badge")}</span>
        <Heading>{t("title")}</Heading>
        <p className="apply-subtitle">{t(asPage ? "pageSubtitle" : "subtitle")}</p>
        <h3 className="apply-steps-title">{t("stepsTitle")}</h3>
        <Steps
          steps={[
            { icon: "request", title: t("step1Title"), text: t("step1Text") },
            { icon: "call", title: t("step2Title"), text: t("step2Text") },
            { icon: "match", title: t("step3Title"), text: t("step3Text") },
            { icon: "work", title: t("step4Title"), text: t("step4Text") },
          ]}
        />
      </div>
      <ApplicationForm {...options} title={t("formTitle")} commentPlaceholder={asPage ? t("pageCommentPlaceholder") : undefined} />
    </section>
  );
}
