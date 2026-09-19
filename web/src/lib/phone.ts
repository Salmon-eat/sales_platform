/**
 * Phone formatting while typing. The API normalises every number (E.164) anyway; this only makes typing
 * easy: the country code appears by itself and the digits fall into the usual groups.
 *   612345678      -> +34 612 345 678        (a Spanish mobile/landline typed without the code)
 *   0671234567     -> +380 (67) 123-45-67    (a Ukrainian number typed the way Ukrainians write it)
 *   +380671234567  -> +380 (67) 123-45-67
 */

type Rule = { code: string; digits: number; format: (d: string) => string };

/** Groups of `sizes` with the given separators: group([3,3,3], [" ", " "]). */
function grouped(d: string, sizes: number[], seps: string[]): string {
  let out = "";
  let at = 0;
  sizes.forEach((size, i) => {
    if (at >= d.length) return;
    if (i > 0) out += seps[i - 1];
    out += d.slice(at, at + size);
    at += size;
  });
  return out;
}

const RULES: Rule[] = [
  {
    code: "380",
    digits: 9,
    format: (d) => (d.length <= 2 ? `(${d}` : `(${d.slice(0, 2)}) ${grouped(d.slice(2), [3, 2, 2], ["-", "-"])}`),
  },
  { code: "34", digits: 9, format: (d) => grouped(d, [3, 3, 3], [" ", " "]) },
  { code: "48", digits: 9, format: (d) => grouped(d, [3, 3, 3], [" ", " "]) },
  { code: "40", digits: 9, format: (d) => grouped(d, [3, 3, 3], [" ", " "]) },
  { code: "373", digits: 8, format: (d) => grouped(d, [2, 3, 3], [" ", " "]) },
  { code: "375", digits: 9, format: (d) => `(${d.slice(0, 2)}${d.length > 2 ? ") " : ""}${grouped(d.slice(2), [3, 2, 2], ["-", "-"])}` },
  { code: "995", digits: 9, format: (d) => grouped(d, [3, 3, 3], [" ", " "]) },
];

export function formatPhone(input: string): string {
  const raw = input.trim();
  let digits = raw.replace(/\D/g, "");
  if (!digits) return raw.startsWith("+") ? "+" : "";

  if (!raw.startsWith("+")) {
    if (digits.startsWith("00")) digits = digits.slice(2); // 00380... = +380...
    else if (digits.startsWith("0")) digits = `38${digits}`; // 067... = Ukrainian
    else if (/^[6789]/.test(digits)) digits = `34${digits}`; // 612... = Spanish
  }

  const rule = RULES.find((r) => digits.startsWith(r.code));
  if (!rule) return `+${digits.slice(0, 15)}`;
  const national = digits.slice(rule.code.length, rule.code.length + rule.digits);
  return national ? `+${rule.code} ${rule.format(national)}` : `+${rule.code}`;
}

/**
 * The next value of the field. Deleting a bracket, space or dash (which formatting would put right back)
 * deletes the digit before it instead, so backspace never gets stuck.
 */
export function nextPhoneValue(previous: string, typed: string): string {
  const digitsOf = (s: string) => s.replace(/\D/g, "");
  if (typed.length < previous.length && digitsOf(typed) === digitsOf(previous)) {
    const digits = digitsOf(previous).slice(0, -1);
    return digits ? formatPhone(`+${digits}`) : "";
  }
  return formatPhone(typed);
}
