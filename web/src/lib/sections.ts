/** The jobs section is the one that differs from the rest of the board: a salary instead of a price, job
 * cards with "apply", professions instead of categories, filters for housing, experience and contract.
 * Everything that has to know asks here (the API has the same rule in SectionRules). */
export const JOBS_SECTION = "empleo";

export const isJobsSection = (key: string | null | undefined): boolean => key === JOBS_SECTION;
