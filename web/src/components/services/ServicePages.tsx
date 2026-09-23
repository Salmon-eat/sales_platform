import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApplicationForm } from "@/components/apply/ApplicationForm";
import { Steps } from "@/components/apply/Steps";
import { PageHero } from "@/components/content/PageHero";
import { RichText } from "@/components/content/RichText";
import type { Locale } from "@/i18n/routing";
import { getContent, getTaxonomy, orFallback } from "@/lib/api";
import { getApplicationOptions } from "@/lib/application-options";
import { localizedPath, prefixed } from "@/lib/routes";
import { absoluteUrl, apiAlternates, jsonLd } from "@/lib/seo";
import type { CategoryNode, ContentBlock, ResolveOut, Taxonomy } from "@/lib/types";

/**
 * Permanent agency services (documents, training): not listings but content pages with an
 * application form. Texts: content blocks service_<category es slug> (title, body, data.summary,
 * data.points); a service without its own text gets a short generic intro.
 */
type Section = Taxonomy["sections"][number];

const contentKey = (node: CategoryNode) => `service_${node.slugs.es}`;

async function load(locale: Locale, resolved: ResolveOut) {
  const taxonomy = await orFallback(getTaxonomy(locale), { sections: [] } as Taxonomy);
  const section = taxonomy.sections.find((s) => s.key === resolved.section?.key);
  const sector = section?.categories.find((c) => c.slugs.es === resolved.sector?.key);
  const service = sector?.children.find((c) => c.slugs.es === resolved.profession?.key);
  return { section, sector, service };
}

const texts = (locale: Locale, nodes: CategoryNode[]) =>
  Promise.all(nodes.map((n) => orFallback<ContentBlock | null>(getContent(contentKey(n), locale), null)));

const servicePath = (locale: Locale, section: Section, node?: CategoryNode) =>
  prefixed(locale, [section.slug, node?.slug].filter(Boolean).join("/"));

export async function servicesMetadata(locale: Locale, resolved: ResolveOut): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "services" });
  const { sector, service } = await load(locale, resolved);
  const content = service ? await orFallback(getContent(contentKey(service), locale), null) : null;
  const title = service ? (content?.title ?? service.name) : sector ? `${sector.name} — ${t("catalogTitle")}` : t("catalogTitle");
  const description = service ? (content?.data.summary as string | undefined) ?? t("genericIntro") : t("catalogSubtitle");
  return { title, description, alternates: apiAlternates(locale, resolved.alternates) };
}

/** /{lang}/{services}: all services by sector; /{lang}/{services}/{sector}: one sector. */
export async function ServicesCatalog({ locale, resolved }: { locale: Locale; resolved: ResolveOut }) {
  const t = await getTranslations("services");
  const { section, sector } = await load(locale, resolved);
  if (!section) return null;
  const sectors = sector ? [sector] : section.categories;
  const summaries = await texts(locale, sectors.flatMap((s) => s.children));
  let i = 0;

  const crumbs = [
    { name: "Citobazar", href: localizedPath(locale, { type: "home" }) },
    ...(sector ? [{ name: t("catalogTitle"), href: servicePath(locale, section) }] : []),
  ];

  return (
    <>
      <PageHero crumbs={crumbs} title={sector ? sector.name : t("catalogTitle")}>
        <p>{t("catalogSubtitle")}</p>
      </PageHero>
      <div className="container services">
        {sectors.map((s) => (
          <section key={s.id}>
            {!sector && (
              <h2 className="section-title">
                <Link href={servicePath(locale, section, s)}>{s.name}</Link>
              </h2>
            )}
            <ul className="service-grid">
              {s.children.map((service) => {
                const content = summaries[i++];
                return (
                  <li key={service.id}>
                    <Link href={servicePath(locale, section, service)} className="service-card">
                      <strong>{content?.title ?? service.name}</strong>
                      <span className="muted">{(content?.data.summary as string | undefined) ?? t("genericIntro")}</span>
                      <span className="service-card-more">
                        {t("more")} <ArrowRight size={16} aria-hidden />
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
        {sector && (
          <Link href={servicePath(locale, section)} className="text-link">
            ← {t("all")}
          </Link>
        )}
      </div>
    </>
  );
}

/** /{lang}/{services}/{service}: description, what is included, application with the service preset. */
export async function ServicePage({ locale, resolved }: { locale: Locale; resolved: ResolveOut }) {
  const t = await getTranslations("services");
  const tAgency = await getTranslations("agency");
  const tApply = await getTranslations("apply");
  const tDrivers = await getTranslations("drivers");
  const { section, sector, service } = await load(locale, resolved);
  if (!section || !sector || !service) return null;

  const [content, options] = await Promise.all([
    orFallback<ContentBlock | null>(getContent(contentKey(service), locale), null),
    getApplicationOptions(locale),
  ]);
  const title = content?.title ?? service.name;
  const [intro, ...rest] = (content?.body ?? t("genericIntro")).split("\n");
  const points = (content?.data.points as string[] | undefined) ?? [];
  const others = sector.children.filter((c) => c.id !== service.id);

  const crumbs = [
    { name: "Citobazar", href: localizedPath(locale, { type: "home" }) },
    { name: t("catalogTitle"), href: servicePath(locale, section) },
    { name: sector.name, href: servicePath(locale, section, sector) },
  ];

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLd([
          {
            "@context": "https://schema.org",
            "@type": "Service",
            name: title,
            description: intro,
            areaServed: { "@type": "Country", name: "ES" },
            provider: { "@type": "Organization", name: "Citobazar", url: absoluteUrl("/") },
          },
          {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: [...crumbs, { name: title, href: servicePath(locale, section, service) }].map((c, i) => ({
              "@type": "ListItem",
              position: i + 1,
              name: c.name,
              item: absoluteUrl(c.href),
            })),
          },
        ])}
      />
      <PageHero crumbs={crumbs} title={title}>
        <p>{intro}</p>
      </PageHero>

      <div className="container drivers">
        <section className="agency-grid">
          <div>
            {points.length > 0 && (
              <>
                <h2 className="section-title">{tAgency("pointsTitle")}</h2>
                <ul className="points">
                  {points.map((p) => (
                    <li key={p}>
                      <CheckCircle2 size={18} aria-hidden /> {p}
                    </li>
                  ))}
                </ul>
              </>
            )}
            {rest.length > 0 && <RichText text={rest.join("\n")} />}
            {others.length > 0 && (
              <div className="service-others">
                <h3>{t("others")}</h3>
                <ul>
                  {others.map((o) => (
                    <li key={o.id}>
                      <Link href={servicePath(locale, section, o)} className="text-link">
                        {o.name} →
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <ApplicationForm sectors={options.sectors} cities={options.cities} categoryId={service.id} title={t("applyTitle")} />
        </section>

        <section>
          <h2 className="section-title">{tApply("stepsTitle")}</h2>
          <Steps
            steps={[
              { icon: "request", title: tApply("step1Title"), text: tApply("step1Text") },
              { icon: "call", title: tApply("step2Title"), text: tApply("step2Text") },
              { icon: "documents", title: tDrivers("step3Title"), text: tDrivers("step3Text") },
            ]}
          />
        </section>
      </div>
    </>
  );
}
