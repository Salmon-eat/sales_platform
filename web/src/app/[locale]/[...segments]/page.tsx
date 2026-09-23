import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { StaticPage } from "@/components/content/StaticPage";
import { DriversPage } from "@/components/drivers/DriversPage";
import { ListingPage, listingMetadata } from "@/components/listing/ListingPage";
import { ListPage, listMetadata } from "@/components/search/ListPage";
import { SearchAll, searchAllMetadata } from "@/components/search/SearchAll";
import { ServicePage, ServicesCatalog, servicesMetadata } from "@/components/services/ServicePages";
import { asLocale, type Locale } from "@/i18n/routing";
import { resolvePath } from "@/lib/api";
import { type AppRoute, localizedPath, prefixed, resolveSegments } from "@/lib/routes";
import type { RawSearchParams } from "@/lib/search-url";
import { routeAlternates, routeRobots } from "@/lib/seo";
import type { ResolveOut } from "@/lib/types";

/**
 * Path resolver (spec §6). Static and agency pages are known to the web app; sections, sectors,
 * professions, features, locations and cards are resolved by GET /v1/resolve (slug history -> 301).
 */
type Props = {
  params: Promise<{ locale: string; segments: string[] }>;
  searchParams: Promise<RawSearchParams>;
};

type Target = { kind: "route"; locale: Locale; route: AppRoute } | { kind: "api"; locale: Locale; resolved: ResolveOut };

function queryString(sp: RawSearchParams): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(sp)) {
    for (const v of Array.isArray(value) ? value : value === undefined ? [] : [value]) qs.append(key, v);
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

async function resolve({ params, searchParams }: Props): Promise<Target> {
  const { locale: raw, segments } = await params;
  const locale = asLocale(raw);
  const decoded = segments.map(decodeURIComponent);
  const local = resolveSegments(locale, decoded);
  if (local) {
    if (local.redirect) permanentRedirect(localizedPath(locale, local.route) + queryString(await searchParams));
    return { kind: "route", locale, route: local.route };
  }
  const resolved = await resolvePath(locale, decoded.join("/"));
  if (resolved.type === "not_found") notFound();
  if (resolved.type === "redirect" && resolved.redirect !== null) {
    permanentRedirect(prefixed(locale, resolved.redirect) + queryString(await searchParams));
  }
  return { kind: "api", locale, resolved };
}

async function routeTitle(locale: Locale, route: AppRoute): Promise<string> {
  const t = await getTranslations({ locale });
  if (route.type === "static") return t(`static.${route.key}`);
  if (route.type === "agency") return t("drivers.title");
  return t("meta.siteName");
}

export async function generateMetadata(props: Props): Promise<Metadata> {
  const target = await resolve(props);
  const { locale } = target;
  if (target.kind === "api") {
    const { resolved } = target;
    if (resolved.type === "listing") return listingMetadata(locale, resolved);
    if (resolved.type === "services" || resolved.type === "service") return servicesMetadata(locale, resolved);
    return listMetadata(locale, resolved, await props.searchParams);
  }
  if (target.route.type === "search") return searchAllMetadata(locale, await props.searchParams);
  const filtered = Object.keys(await props.searchParams).length > 0;
  return {
    title: await routeTitle(locale, target.route),
    alternates: routeAlternates(locale, target.route),
    robots: filtered ? { index: false, follow: true } : routeRobots(target.route),
  };
}

export default async function ResolvedPage(props: Props) {
  const target = await resolve(props);
  const { locale } = target;
  setRequestLocale(locale);

  if (target.kind === "api") {
    const { resolved } = target;
    if (resolved.type === "listing") return <ListingPage locale={locale} resolved={resolved} />;
    if (resolved.type === "services") return <ServicesCatalog locale={locale} resolved={resolved} />;
    if (resolved.type === "service") return <ServicePage locale={locale} resolved={resolved} />;
    return <ListPage locale={locale} resolved={resolved} searchParams={await props.searchParams} />;
  }

  const { route } = target;
  if (route.type === "search") return <SearchAll locale={locale} searchParams={await props.searchParams} />;
  if (route.type === "agency") return <DriversPage locale={locale} />;
  if (route.type === "static") {
    const { tab } = await props.searchParams;
    return <StaticPage locale={locale} page={route.key} title={await routeTitle(locale, route)} tab={typeof tab === "string" ? tab : undefined} />;
  }
  notFound();
}
