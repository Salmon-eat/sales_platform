"use client";

import type { ReactNode } from "react";

/** A submit button that asks first: deleting the account cannot be undone. */
export function ConfirmSubmit({
  question,
  className,
  children,
}: {
  question: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="submit"
      className={className}
      onClick={(event) => {
        if (!confirm(question)) event.preventDefault();
      }}
    >
      {children}
    </button>
  );
}
