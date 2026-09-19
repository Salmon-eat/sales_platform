"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { track } from "@/lib/analytics";
import { markViewed } from "@/lib/saved";

/** Page views and the time a page was actually visible (a background tab does not count). */
export function Analytics() {
  const pathname = usePathname();

  useEffect(() => {
    let visibleSince: number | null = document.visibilityState === "visible" ? Date.now() : null;
    let visibleMs = 0;
    let sent = false;
    track("page_view");

    const pause = () => {
      if (visibleSince !== null) visibleMs += Date.now() - visibleSince;
      visibleSince = null;
    };
    const leave = () => {
      if (sent) return;
      pause();
      sent = true;
      // React dev mode mounts effects twice; a "visit" of a few ms is not a real page view
      // on client navigation the address has already changed: report the page that was left
      if (visibleMs >= 300) track("page_leave", { duration_ms: visibleMs, path: pathname });
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        visibleSince = Date.now();
        return;
      }
      pause();
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", leave);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", leave);
      leave(); // client-side navigation to another page
    };
  }, [pathname]);

  return null;
}

/** Card page: "someone looked at this job" for the views -> applications numbers; in this browser the
 * job's cards now show it was opened. */
export function TrackListingView({ listingId }: { listingId: number }) {
  useEffect(() => {
    track("listing_view", { listing_id: listingId });
    markViewed(listingId);
  }, [listingId]);
  return null;
}
