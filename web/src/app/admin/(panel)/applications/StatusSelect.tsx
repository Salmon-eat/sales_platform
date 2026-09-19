"use client";

import { useTransition } from "react";

import type { ApplicationStatus } from "@/lib/types";

import { setApplicationStatus } from "../../actions";

type Props = {
  id: number;
  value: ApplicationStatus;
  options: readonly (readonly [string, string])[];
  label: string;
};

/** Saves as soon as another status is picked. */
export function StatusSelect({ id, value, options, label }: Props) {
  const [pending, startTransition] = useTransition();

  return (
    <select
      aria-label={label}
      defaultValue={value}
      disabled={pending}
      className={`status-select status-select--${value}`}
      onChange={(e) => {
        const form = new FormData();
        form.set("id", String(id));
        form.set("status", e.currentTarget.value);
        startTransition(() => setApplicationStatus(form));
      }}
    >
      {options.map(([v, text]) => (
        <option key={v} value={v}>
          {text}
        </option>
      ))}
    </select>
  );
}
