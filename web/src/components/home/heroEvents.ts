/** The event the search box sends when a section is picked (detail: the section key, or null for all);
 * the 3D objects behind the search bring that section's object forward. Kept apart so the search
 * does not pull the 3D code into its bundle. */
export const HERO_SECTION_EVENT = "hero:section";

export function announceHeroSection(key: string | null) {
  window.dispatchEvent(new CustomEvent(HERO_SECTION_EVENT, { detail: key }));
}
