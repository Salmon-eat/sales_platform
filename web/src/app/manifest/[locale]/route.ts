import { NextResponse } from "next/server";

import { isLocale, localePrefix } from "@/i18n/routing";

/** The file that lets a phone keep the site as an app. One per language, so the app opens in the
 * language the person installed it from, with its name and description in that language. */
const NAMES: Record<string, { name: string; short: string; description: string }> = {
  es: {
    name: "Citobazar — anuncios en España",
    short: "Citobazar",
    description: "Empleo, pisos, coches, servicios y cosas de segunda mano en España.",
  },
  en: {
    name: "Citobazar — classifieds in Spain",
    short: "Citobazar",
    description: "Jobs, flats, cars, services and second-hand things in Spain.",
  },
  uk: {
    name: "Citobazar — оголошення в Іспанії",
    short: "Citobazar",
    description: "Робота, житло, транспорт, послуги й речі в Іспанії.",
  },
  ru: {
    name: "Citobazar — объявления в Испании",
    short: "Citobazar",
    description: "Работа, жильё, транспорт, услуги и вещи в Испании.",
  },
};

export function generateStaticParams() {
  return Object.keys(NAMES).map((locale) => ({ locale }));
}

export async function GET(_request: Request, { params }: { params: Promise<{ locale: string }> }) {
  const raw = (await params).locale.replace(/\.webmanifest$/, "");
  const locale = isLocale(raw) ? raw : "es";
  const text = NAMES[locale];

  return NextResponse.json(
    {
      id: `citobazar-${locale}`,
      name: text.name,
      short_name: text.short,
      description: text.description,
      lang: locale,
      start_url: `${localePrefix(locale)}?source=app`,
      scope: "/",
      display: "standalone",
      orientation: "portrait",
      background_color: "#f6f2ea",
      theme_color: "#ff6a1a",
      icons: [
        { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
        { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        { src: "/icon-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      ],
    },
    { headers: { "Content-Type": "application/manifest+json", "Cache-Control": "public, max-age=3600" } },
  );
}
