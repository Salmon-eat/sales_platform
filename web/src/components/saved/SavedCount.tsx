"use client";

import { useFavorites } from "@/lib/saved";

/** Number of saved listings as a small badge on the heart icons (header, bottom nav). */
export function SavedCount() {
  const { ids } = useFavorites();
  if (ids.length === 0) return null;
  return <span className="saved-count">{ids.length > 99 ? "99+" : ids.length}</span>;
}
