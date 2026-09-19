import type { Metadata } from "next";
import { Onest } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import type { ReactNode } from "react";

import { adminT, getAdminLocale } from "@/lib/admin-locale";

import "../globals.css";

const onest = Onest({ subsets: ["latin", "cyrillic"], display: "swap", variable: "--font-sans" });

export async function generateMetadata(): Promise<Metadata> {
  const t = await adminT("common");
  return { title: t("title"), robots: { index: false, follow: false } };
}

// Separate root layout: the admin lives outside the site routing; its language is each staff member's
// choice (admin_locale cookie), independent of the site language.
export default async function AdminRootLayout({ children }: { children: ReactNode }) {
  const locale = await getAdminLocale();
  const { admin } = await getMessages({ locale });

  return (
    // browser extensions (LanguageTool, Grammarly, translators) add attributes to <html> before React loads
    <html lang={locale} className={onest.variable} suppressHydrationWarning>
      <body>
        <NextIntlClientProvider locale={locale} messages={{ admin }}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
