"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

type Props = {
  /** query key: "price", "a.year", "a.km" */
  param: string;
  label: string;
  unit: string | null;
  /** what the ads on offer span: shown as the inputs' hints */
  min: number | null;
  max: number | null;
  from: number | null;
  to: number | null;
  /** the current list without this filter; the chosen range is added to it */
  base: string;
  locale: string;
};

const digits = (text: string) => text.replace(/\D/g, "");

/**
 * "From – to" (price, year, kilometres), the way every classifieds site has it. The rest of the page
 * is plain links; this is the one filter that needs typing, so it is the one small client piece.
 */
export function RangeFilter({ param, label, unit, min, max, from, to, base, locale }: Props) {
  const t = useTranslations("search");
  const router = useRouter();
  const [lo, setLo] = useState(from === null ? "" : String(from));
  const [hi, setHi] = useState(to === null ? "" : String(to));
  const number = new Intl.NumberFormat(locale);
  // a year is not "2 016"
  const hint = (n: number | null) => (n === null ? "" : param === "a.year" ? String(n) : number.format(n));

  function apply(event: FormEvent) {
    event.preventDefault();
    const a = digits(lo);
    const b = digits(hi);
    const [url, query = ""] = base.split("?");
    const params = new URLSearchParams(query);
    params.delete(param);
    params.delete("page");
    if (a || b) params.set(param, `${a}-${b}`);
    const rest = params.toString().replace(/%2C/g, ",");
    router.push(rest ? `${url}?${rest}` : url, { scroll: false });
  }

  return (
    <form className="facet-group facet-range" onSubmit={apply}>
      <h3>
        {label}
        {unit && <span className="facet-range__unit">, {unit}</span>}
      </h3>
      <div className="facet-range__row">
        <input
          inputMode="numeric"
          aria-label={`${label}: ${t("rangeFrom")}`}
          placeholder={min === null ? t("rangeFrom") : `${t("rangeFrom")} ${hint(min)}`}
          value={lo}
          onChange={(e) => setLo(e.target.value)}
        />
        <span aria-hidden>–</span>
        <input
          inputMode="numeric"
          aria-label={`${label}: ${t("rangeTo")}`}
          placeholder={max === null ? t("rangeTo") : `${t("rangeTo")} ${hint(max)}`}
          value={hi}
          onChange={(e) => setHi(e.target.value)}
        />
        <button type="submit" className="btn btn--outline btn--sm">
          {t("rangeApply")}
        </button>
      </div>
    </form>
  );
}
