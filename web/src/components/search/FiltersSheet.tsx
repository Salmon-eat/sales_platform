"use client";

import { SlidersHorizontal, X } from "lucide-react";
import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";

const KEY = "bazarcito:filters-sheet";

/** Where the panel was scrolled when a filter was clicked. A city or sector filter opens another page and the
 * panel is drawn anew; without this it would jump back to the top. Kept only for a few seconds, so a new
 * visit to the list starts at the top. */
const kept = { panel: 0, body: 0, at: 0 };
const KEEP_MS = 15_000;

type Props = {
  children: ReactNode;
  total: number;
  activeCount: number;
  labels: { filters: string; close: string; show: string };
};

/**
 * Desktop: the filters are a left panel. Mobile: a bottom sheet with "Show N" (spec §5).
 * Every filter is a link, so the page re-renders on tap; the sheet stays open across that navigation.
 */
export function FiltersSheet({ children, total, activeCount, labels }: Props) {
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLElement>(null);
  const body = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (Date.now() - kept.at > KEEP_MS) return;
    if (panel.current) panel.current.scrollTop = kept.panel;
    if (body.current) body.current.scrollTop = kept.body;
  }, []);

  function remember() {
    kept.panel = panel.current?.scrollTop ?? 0;
    kept.body = body.current?.scrollTop ?? 0;
    kept.at = Date.now();
  }

  useEffect(() => {
    try {
      if (sessionStorage.getItem(KEY) === "1") setOpen(true);
    } catch {
      /* storage blocked */
    }
  }, []);

  useEffect(() => {
    try {
      if (open) sessionStorage.setItem(KEY, "1");
      else sessionStorage.removeItem(KEY);
    } catch {
      /* storage blocked */
    }
    document.body.classList.toggle("sheet-open", open);
    return () => document.body.classList.remove("sheet-open");
  }, [open]);

  return (
    <>
      <button type="button" className="btn btn--ghost-dark btn--sm filters-button" onClick={() => setOpen(true)}>
        <SlidersHorizontal size={15} aria-hidden /> {labels.filters}
        {activeCount > 0 && <span className="count-badge">{activeCount}</span>}
      </button>
      {open && <div className="sheet-backdrop" onClick={() => setOpen(false)} aria-hidden />}
      <aside
        ref={panel}
        className={open ? "search-filters search-filters--open" : "search-filters"}
        aria-label={labels.filters}
        onClickCapture={remember}
      >
        <div className="sheet-head">
          <strong>{labels.filters}</strong>
          <button type="button" className="icon-btn" aria-label={labels.close} onClick={() => setOpen(false)}>
            <X size={20} />
          </button>
        </div>
        <div ref={body} className="sheet-body">
          {children}
        </div>
        <div className="sheet-foot">
          <button type="button" className="btn btn--primary btn--lg btn--block" onClick={() => setOpen(false)}>
            {labels.show.replace("{count}", String(total))}
          </button>
        </div>
      </aside>
    </>
  );
}
