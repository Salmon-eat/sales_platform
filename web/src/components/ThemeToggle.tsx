"use client";

import { Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { THEME_KEY } from "@/lib/theme";

type Theme = "light" | "dark";

function current(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

/** Light / dark switch in the header; the choice is remembered in this browser. */
export function ThemeToggle() {
  const t = useTranslations("header");
  const [theme, setTheme] = useState<Theme | null>(null);

  // the light theme is the default for everyone; the device setting is not followed
  useEffect(() => setTheme(current()), []);

  function toggle() {
    const next: Theme = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* storage blocked: the theme lasts until reload */
    }
    setTheme(next);
  }

  const dark = theme === "dark";
  return (
    <button
      type="button"
      className="icon-button theme-toggle"
      onClick={toggle}
      aria-label={t(dark ? "themeLight" : "themeDark")}
      title={t(dark ? "themeLight" : "themeDark")}
    >
      {dark ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}
