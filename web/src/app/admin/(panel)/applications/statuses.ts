import type { ApplicationStatus } from "@/lib/types";

/** API status → message key in admin.applications.status */
export const STATUSES = {
  new: "new",
  in_progress: "inProgress",
  done: "done",
  rejected: "rejected",
} as const satisfies Record<ApplicationStatus, string>;
