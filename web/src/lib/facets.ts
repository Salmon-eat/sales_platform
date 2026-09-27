import type { FacetGroup } from "./types";

/** Any "search" translator: the server one (getTranslations) and the client one (useTranslations). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Translate = (key: any, values?: any) => string;

/** A filter group's heading: the dictionary's label for attributes, the site's own words for the rest. */
export function facetTitle(group: FacetGroup, t: Translate): string {
  return group.label ?? t(group.key);
}

/** One value of a filter group, as a person reads it: "Неповний день", "від 1 500 €", "Українською". */
export function facetValueLabel(group: FacetGroup, value: string, label: string | null, t: Translate): string {
  // attributes and section tags (a.<key>) come with labels from the dictionary
  if (group.key.startsWith("a.")) return label ?? group.label ?? t("yes");
  if (group.type === "bool") return t(group.key);
  if (group.key === "salary_min") return t("salaryValue", { amount: value });
  if (group.key === "radius") return t("radiusValue", { km: value });
  return t(`${group.key}_${value}`);
}

/** The value a yes/no group is switched on with ("posted" is switched on with its only period). */
export const onValue = (group: FacetGroup): string => (group.type === "bool" ? "1" : (group.values[0]?.value ?? "1"));
