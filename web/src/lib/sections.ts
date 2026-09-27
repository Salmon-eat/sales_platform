/** The jobs section is the one that differs from the rest of the board: a salary instead of a price, job
 * cards with "apply", professions instead of categories, filters for housing, experience and contract.
 * Everything that has to know asks here (the API has the same rule in SectionRules). */
export const JOBS_SECTION = "empleo";

export const isJobsSection = (key: string | null | undefined): boolean => key === JOBS_SECTION;

/** A filter as it sits in the address: its key and one value ("housing", "1"; "schedule", "part"). */
export type FilterChoice = [key: string, value: string];

type SectionUi = {
  /** the "what are you looking for?" panel on the home page: its groups, in this order.
   * Yes/no filters among them go together into the first row. */
  picker?: string[];
  /** groups the panel keeps folded at its end: open to everyone, needed by some */
  pickerMore?: string[];
  /** one-click buttons above the list, the way Jobtoday does it */
  quick?: FilterChoice[];
  /** one more button that follows the language the site is read in: the team speaks it too */
  quickInOwnLanguage?: (locale: string) => FilterChoice | null;
};

/**
 * What each section offers on top of its plain filters. Data, not code: another section gets its own
 * panel or buttons by adding a line here; the components read whatever is listed.
 *
 * Nothing here guesses who the visitor is. The site is Spanish and its visitors are of every kind: a
 * Spaniard, a Ukrainian with Spanish citizenship reading in Ukrainian, a newcomer reading in Spanish. The
 * language of the interface says how somebody likes to read, not what papers they have, so everybody is
 * offered the same filters; the ones about languages and papers sit folded at the end for whoever needs
 * them.
 */
export const SECTION_UI: Record<string, SectionUi> = {
  [JOBS_SECTION]: {
    picker: ["housing", "no_experience", "a.official", "schedule", "contract", "a.suitable_for", "a.benefits", "salary_min"],
    pickerMore: ["no_language", "a.team_language", "a.documents"],
    quick: [
      ["housing", "1"],
      ["no_experience", "1"],
      ["schedule", "part"],
      ["schedule", "weekends"],
      ["contract", "indefinido"],
      ["a.suitable_for", "students"],
    ],
    // reading in Ukrainian says nothing about papers, but a team that speaks Ukrainian is a comfort worth
    // one click; Spanish is taken for granted on a Spanish site
    quickInOwnLanguage: (locale) => (locale === "es" ? null : ["a.team_language", locale]),
  },
};

export const sectionUi = (key: string | null | undefined): SectionUi => (key && SECTION_UI[key]) || {};

/** The one-click buttons for this section, in the visitor's language. */
export function quickFilters(sectionKey: string | null | undefined, locale: string): FilterChoice[] {
  const ui = sectionUi(sectionKey);
  const own = ui.quickInOwnLanguage?.(locale);
  return [...(ui.quick ?? []), ...(own ? [own] : [])];
}
