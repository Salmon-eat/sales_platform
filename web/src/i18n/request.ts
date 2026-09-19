import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";

import { loadAdminMessages } from "../../messages/admin";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;

  return {
    locale,
    // the admin texts live under "admin"; the public layout passes only the site texts to the browser
    messages: {
      ...(await import(`../../messages/${locale}.json`)).default,
      admin: await loadAdminMessages(locale),
    },
  };
});
