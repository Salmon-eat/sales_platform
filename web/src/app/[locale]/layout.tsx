import type { Metadata, Viewport } from "next";
import { Onest, Unbounded } from "next/font/google";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { Analytics } from "@/components/Analytics";
import { BottomNav } from "@/components/BottomNav";
import { ContactWidget } from "@/components/ContactWidget";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { THEME_SCRIPT } from "@/lib/theme";
import { routing } from "@/i18n/routing";
import { getContent } from "@/lib/api";
import { localizedPath } from "@/lib/routes";
import { SITE_URL } from "@/lib/seo";

import "../globals.css";

// spec §11: Onest for all text, Unbounded 500 only for the logo and main headings (next/font self-hosts both)
const onest = Onest({ subsets: ["latin", "cyrillic"], weight: ["400", "500", "600"], display: "swap", variable: "--font-sans" });
const unbounded = Unbounded({ subsets: ["latin", "cyrillic"], weight: "500", display: "swap", variable: "--font-display" });

type Props = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#1b1e24" },
  ],
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const t = await getTranslations({ locale, namespace: "meta" });

  return {
    metadataBase: new URL(SITE_URL),
    title: { default: t("title"), template: `%s | ${t("siteName")}` },
    description: t("description"),
    openGraph: { siteName: t("siteName"), locale, type: "website" },
  };
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  // the browser gets the site texts only, not the admin ones
  const { admin: _admin, ...messages } = await getMessages();
  // messengers for the floating "write to a manager" orange; the contact page's data is the one source
  const contact = await getContent("contact", locale)
    .then((c) => c.data as { telegram?: string; whatsapp?: string; viber?: string; hours?: string })
    .catch(() => ({}) as Record<string, undefined>);

  return (
    // browser extensions (LanguageTool, Grammarly, translators) add attributes to <html> before React loads
    <html lang={locale} className={`${onest.variable} ${unbounded.variable}`} suppressHydrationWarning>
      <head>
        {/* the light/dark theme before the first paint */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <NextIntlClientProvider messages={messages}>
          <Header />
          <main>{children}</main>
          <Footer />
          <BottomNav />
          <ContactWidget
            telegram={contact.telegram}
            whatsapp={contact.whatsapp}
            viber={contact.viber}
            hours={contact.hours}
            requestHref={localizedPath(locale, { type: "static", key: "request" })}
          />
          <Analytics />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
