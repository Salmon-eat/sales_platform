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
};

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
  },
};

export const sectionUi = (key: string | null | undefined): SectionUi => (key && SECTION_UI[key]) || {};
