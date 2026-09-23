"use client";

import { useTranslations } from "next-intl";

import type { Lang, ListingQuestionSetting, QuestionPreset } from "@/lib/types";

const LANGS: Lang[] = ["es", "en", "uk", "ru"];
const CUSTOM = ["custom1", "custom2"] as const;
const MAX = 6;
const langCode = (lang: Lang) => (lang === "uk" ? "UA" : lang.toUpperCase());

type Props = {
  presets: QuestionPreset[];
  value: ListingQuestionSetting[];
  onChange: (next: ListingQuestionSetting[]) => void;
  disabled?: boolean;
};

/**
 * Optional questions to the candidate. Ready-made ones are ticked (already translated into the 4 site
 * languages); an own yes/no question is typed per language, like the listing text. The candidate may skip them.
 */
export function QuestionsFieldset({ presets, value, onChange, disabled }: Props) {
  const t = useTranslations("admin.listings");
  const chosen = new Set(value.map((q) => q.key));
  const full = value.length >= MAX;

  function toggle(key: string) {
    onChange(chosen.has(key) ? value.filter((q) => q.key !== key) : [...value, { key }]);
  }

  function setCustom(key: string, lang: Lang, text: string) {
    const current = value.find((q) => q.key === key);
    const nextText = { ...(current?.text ?? {}), [lang]: text };
    const filled = Object.values(nextText).some((v) => v?.trim());
    const others = value.filter((q) => q.key !== key);
    onChange(filled ? [...others, { key, text: nextText }] : others);
  }

  return (
    <fieldset className="panel" disabled={disabled}>
      <legend>{t("form.questionsTitle")}</legend>
      <p className="muted small">{t("form.questionsHint", { max: MAX })}</p>
      <div className="question-presets">
        {presets.map((p) => (
          <label key={p.key} className="check">
            <input type="checkbox" checked={chosen.has(p.key)} disabled={!chosen.has(p.key) && full} onChange={() => toggle(p.key)} />
            {p.text}
          </label>
        ))}
      </div>
      {CUSTOM.map((key, i) => {
        const current = value.find((q) => q.key === key);
        return (
          <div key={key} className="question-custom">
            <span className="question-custom__title">{t("form.questionOwn", { n: i + 1 })}</span>
            <div className="question-custom__langs">
              {LANGS.map((lang) => (
                <label key={lang} className="field">
                  <span>{langCode(lang)}</span>
                  <input
                    maxLength={200}
                    value={current?.text?.[lang] ?? ""}
                    disabled={!current && full}
                    placeholder={t("form.questionOwnPlaceholder")}
                    onChange={(e) => setCustom(key, lang, e.target.value)}
                  />
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </fieldset>
  );
}
