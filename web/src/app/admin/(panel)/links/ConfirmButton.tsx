"use client";

import type { ReactNode } from "react";

/** Submit button that asks first (closing a link cannot be undone). */
export function ConfirmButton({ question, className, children }: { question: string; className?: string; children: ReactNode }) {
  return (
    <button
      type="submit"
      className={className}
      onClick={(e) => {
        if (!window.confirm(question)) e.preventDefault();
      }}
    >
      {children}
    </button>
  );
}
