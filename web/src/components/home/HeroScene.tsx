"use client";

import { useEffect, useRef } from "react";

/** The floating 3D section objects behind the home search. Only on wide screens and when the visitor
 * has not asked for less motion; the 3D code loads after the page, so the search is never kept waiting. */
export function HeroScene() {
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wide = window.matchMedia("(min-width: 1200px) and (prefers-reduced-motion: no-preference)");
    let cancelled = false;
    let stop: (() => void) | undefined;
    let turn = 0; // a load that finishes after the window changed again is dropped
    // follows the window: widened later, the objects appear; narrowed, they go
    const sync = () => {
      if (wide.matches && !stop) {
        const mine = ++turn;
        stop = () => undefined; // taken while the 3D code loads
        import("./hero3d")
          .then(({ mountHeroScene }) => {
            if (mine !== turn) return;
            if (cancelled || !box.current) stop = undefined;
            else stop = mountHeroScene(box.current);
          })
          .catch(() => (stop = undefined));
      } else if (!wide.matches && stop) {
        turn++;
        stop();
        stop = undefined;
        box.current?.classList.remove("is-ready");
      }
    };
    sync();
    wide.addEventListener("change", sync);
    return () => {
      cancelled = true;
      wide.removeEventListener("change", sync);
      stop?.();
    };
  }, []);

  return <div ref={box} className="hero-scene" aria-hidden />;
}
