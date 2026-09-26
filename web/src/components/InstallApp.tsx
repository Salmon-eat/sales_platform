"use client";

import { Download, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

const HIDDEN_KEY = "cb_install_hidden";

/**
 * Two small jobs: keep the service worker registered, and — when the browser says the site can be
 * installed — offer it once. Somebody who says no is not asked again on this device.
 */
export function InstallApp() {
  const t = useTranslations("install");
  const [event, setEvent] = useState<InstallEvent | null>(null);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    const hidden = (() => {
      try {
        return localStorage.getItem(HIDDEN_KEY) === "1";
      } catch {
        return false;
      }
    })();
    if (hidden) return;

    const onPrompt = (raw: Event) => {
      raw.preventDefault();
      setEvent(raw as InstallEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  function hide() {
    setEvent(null);
    try {
      localStorage.setItem(HIDDEN_KEY, "1");
    } catch {
      // a private window: we simply ask again next time
    }
  }

  async function install() {
    if (!event) return;
    await event.prompt();
    await event.userChoice;
    hide();
  }

  if (!event) return null;

  return (
    <div className="install-bar" role="dialog" aria-label={t("title")}>
      <div>
        <strong>{t("title")}</strong>
        <p className="muted small">{t("text")}</p>
      </div>
      <button type="button" className="btn btn--primary btn--sm" onClick={install}>
        <Download size={15} aria-hidden /> {t("install")}
      </button>
      <button type="button" className="icon-button" onClick={hide} aria-label={t("later")}>
        <X size={18} />
      </button>
    </div>
  );
}
