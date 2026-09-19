import "server-only";

import { adminT } from "./admin-locale";

type Detail = string | { msg?: string; loc?: (string | number)[] }[] | undefined | null;

/**
 * API admin errors are codes ("publish_needs_es", "attr_value:trailer_type", pydantic
 * "Value error, salary_range"); this turns them into sentences in the admin language.
 * Unknown texts (e.g. pydantic's own "Field required") are shown with the field name.
 */
export async function translateApiErrors(detail: Detail): Promise<string[]> {
  const t = await adminT("errors");
  const known = (code: string, key?: string): string | null =>
    t.has(code as "generic") ? t(code as "attr_value", { key: key ?? "" }) : null;

  const one = (raw: string, field?: string): string => {
    const text = raw.replace(/^Value error, /, "");
    const [code, key] = text.split(":");
    return known(code, key) ?? (field ? `${field}: ${text}` : text);
  };

  if (!detail) return [t("generic")];
  if (typeof detail === "string") return [one(detail)];
  if (!Array.isArray(detail) || detail.length === 0) return [t("generic")];
  return detail.map((d) => one(d.msg ?? t("generic"), (d.loc ?? []).filter((p) => p !== "body").join(".") || undefined));
}
