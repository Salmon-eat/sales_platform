import { Clock, Mail, Phone, Send } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { redirect } from "next/navigation";

import { myChats } from "@/app/[locale]/chat-actions";
import { myCandidates } from "@/app/[locale]/employer-actions";
import { getResume } from "@/app/[locale]/resume-actions";
import { AccountPanel } from "@/components/account/AccountPanel";
import { Candidates } from "@/components/account/Candidates";
import { Chats } from "@/components/account/Chats";
import { MyAds } from "@/components/account/MyAds";
import { ResumeForm } from "@/components/account/ResumeForm";
import { SignInForm } from "@/components/account/SignInForm";
import { ApplicationSection } from "@/components/apply/ApplicationSection";
import { PostPage } from "@/components/post/PostPage";
import { AccountTabs } from "@/components/saved/AccountTabs";
import type { Locale } from "@/i18n/routing";
import { getAccount } from "@/lib/account";
import { getContent, getPopularLocations, orFallback } from "@/lib/api";
import { getApplicationOptions } from "@/lib/application-options";
import { localizedPath, type StaticKey } from "@/lib/routes";
import { jsonLd } from "@/lib/seo";

import { EmployerRequestForm } from "./EmployerRequestForm";
import { PageHero } from "./PageHero";
import { RichText } from "./RichText";

type FaqItem = { q: string; a: string };

type Props = { locale: Locale; page: StaticKey; title: string; tab?: string; edit?: string };

export async function StaticPage({ locale, page, title, tab, edit }: Props) {
  const crumbs = [{ name: "Citobazar", href: localizedPath(locale, { type: "home" }) }];
  if (page === "account") {
    // signed in: the profile is on top; saved listings and applications still come from this browser
    const account = await getAccount();
    return (
      <>
        <PageHero crumbs={crumbs} title={title} />
        <div className="container static-page">
          <AccountPanel account={account} locale={locale} />
          {account && <Chats initial={await myChats(locale)} />}
          {account && <Candidates initial={await myCandidates(locale)} />}
          {account && <MyAds locale={locale} />}
          {account && (
            <ResumeForm
              initial={await getResume(locale)}
              cities={(await orFallback(getPopularLocations(locale, 50), []))
                .filter((place): place is typeof place & { id: number } => typeof place.id === "number")
                .sort((a, b) => a.name.localeCompare(b.name, locale))}
            />
          )}
          <AccountTabs key={tab} initialTab={tab === "applied" ? "applied" : "saved"} />
        </div>
      </>
    );
  }
  if (page === "login") {
    if (await getAccount()) redirect(localizedPath(locale, { type: "static", key: "account" }));
    return (
      <div className="container static-page static-page--narrow">
        <SignInForm />
      </div>
    );
  }
  if (page === "request") {
    const { sectors, cities } = await getApplicationOptions(locale);
    return (
      <div className="container static-page">
        <nav className="breadcrumbs">
          <Link href={crumbs[0].href}>{crumbs[0].name}</Link>
          <span aria-hidden>›</span>
          <span>{title}</span>
        </nav>
        <ApplicationSection options={{ sectors, cities }} asPage />
      </div>
    );
  }
  const t = await getTranslations("contactPage");
  const content = await getContent(page, locale);

  if (page === "faq") {
    const items = (content.data.items as FaqItem[] | undefined) ?? [];
    return (
      <>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={jsonLd({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: items.map((i) => ({ "@type": "Question", name: i.q, acceptedAnswer: { "@type": "Answer", text: i.a } })),
          })}
        />
        <PageHero crumbs={crumbs} title={content.title} />
        <div className="container static-page">
          <div className="faq">
            {items.map((item, i) => (
              <details key={item.q} className="faq-item" open={i === 0}>
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </>
    );
  }

  if (page === "publish") {
    // the board's own form; a company that wants us to post a job for them writes below it
    return (
      <>
        <PostPage locale={locale} title={content.title} editId={/^\d+$/.test(edit ?? "") ? Number(edit) : undefined} />
        <div className="container static-page static-page--narrow">
          <EmployerRequestForm />
        </div>
      </>
    );
  }

  if (page === "contact") {
    const data = content.data as { telegram?: string; email?: string; phone?: string; hours?: string };
    return (
      <>
        <PageHero crumbs={crumbs} title={content.title} />
        <div className="container static-page">
          <RichText text={content.body} />
          <div className="contact-cards">
            {data.telegram && (
              <a className="contact-card contact-card--accent" href={data.telegram} rel="noopener">
                <Send size={22} aria-hidden />
                <span>{t("telegram")}</span>
                <strong>{t("write")}</strong>
              </a>
            )}
            {data.email && (
              <a className="contact-card" href={`mailto:${data.email}`}>
                <Mail size={22} aria-hidden />
                <span>{t("email")}</span>
                <strong>{data.email}</strong>
              </a>
            )}
            {data.phone && (
              <a className="contact-card" href={`tel:${data.phone.replace(/\s/g, "")}`}>
                <Phone size={22} aria-hidden />
                <span>{t("phone")}</span>
                <strong>{data.phone}</strong>
              </a>
            )}
            {data.hours && (
              <div className="contact-card">
                <Clock size={22} aria-hidden />
                <span>{t("hours")}</span>
                <strong>{data.hours}</strong>
              </div>
            )}
          </div>
        </div>
      </>
    );
  }

  // privacy
  return (
    <>
      <PageHero crumbs={crumbs} title={content.title} />
      <div className="container static-page static-page--narrow">
        <RichText text={content.body} />
      </div>
    </>
  );
}
