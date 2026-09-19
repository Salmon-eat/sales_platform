import type messages from "../../messages/uk.json";
import type { AdminMessages } from "../../messages/admin";
import type { Locale } from "@/i18n/routing";

declare module "next-intl" {
  interface AppConfig {
    Locale: Locale;
    Messages: typeof messages & { admin: AdminMessages };
  }
}
