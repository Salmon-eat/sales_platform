/** The jobs section is the one that differs from the rest of the board: a salary instead of a price, job
 * cards with "apply", professions instead of categories, filters for housing, experience and contract.
 * Everything that has to know asks here (the API has the same rule in SectionRules). */
export const JOBS_SECTION = "empleo";

export const isJobsSection = (key: string | null | undefined): boolean => key === JOBS_SECTION;

/** A filter as it sits in the address: its key and one value ("housing", "1"; "schedule", "part"). */
export type FilterChoice = [key: string, value: string];

type SectionUi = {
  /** the "what are you looking for?" window on the home page: its groups, in this order.
   * Yes/no filters among them go together into the first row. */
  picker?: string[];
  /** one-click buttons above the list, the way Jobtoday does it */
  quick?: FilterChoice[];
  /** filters that matter to somebody new in Spain (no Spanish yet, papers, a team that speaks their
   * language) and mean nothing to a Spaniard: offered up front only to newcomers (see isNewcomer) */
  newcomers?: string[];
};

/**
 * The site is Spanish; its visitors are mostly Spaniards, and Ukrainians (and other newcomers) are one of
 * its audiences. Who reads it in Spanish is taken for a local; in Ukrainian, Russian or English, for
 * somebody who came to Spain and may need a job without Spanish or help with papers.
 */
const NEWCOMER_LOCALES = new Set(["uk", "ru", "en"]);
export const isNewcomer = (locale: string): boolean => NEWCOMER_LOCALES.has(locale);

/**
 * What each section offers on top of its plain filters. Data, not code: another section gets its own
 * window or buttons by adding a line here; the components read whatever is listed.
 */
export const SECTION_UI: Record<string, SectionUi> = {
  [JOBS_SECTION]: {
    picker: [
      "housing",
      "no_experience",
      "no_language",
      "a.official",
      "a.team_language",
      "a.documents",
      "schedule",
      "contract",
      "a.suitable_for",
      "a.benefits",
      "salary_min",
    ],
    quick: [
      ["housing", "1"],
      ["no_experience", "1"],
      ["no_language", "1"],
      ["a.team_language", "uk"],
      ["a.documents", "temporary_protection"],
      ["schedule", "part"],
      ["schedule", "weekends"],
      ["a.suitable_for", "students"],
    ],
    newcomers: ["no_language", "a.team_language", "a.documents"],
  },
};

export const sectionUi = (key: string | null | undefined): SectionUi => (key && SECTION_UI[key]) || {};

/** Is this filter group for newcomers only, in this section? */
export const forNewcomers = (sectionKey: string | null | undefined, groupKey: string): boolean =>
  (sectionUi(sectionKey).newcomers ?? []).includes(groupKey);

/** What this visitor is offered up front: the section's list without the newcomers' filters for a local. */
export function forAudience<T>(sectionKey: string | null | undefined, locale: string, items: T[], keyOf: (item: T) => string): T[] {
  return isNewcomer(locale) ? items : items.filter((item) => !forNewcomers(sectionKey, keyOf(item)));
}
