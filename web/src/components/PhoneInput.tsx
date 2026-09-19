"use client";

import { type ComponentProps, useState } from "react";

import { formatPhone, nextPhoneValue } from "@/lib/phone";

type Props = Omit<ComponentProps<"input">, "value" | "onChange" | "type"> & { defaultValue?: string };

/** A phone field that adds the country code and groups the digits as the person types. */
export function PhoneInput({ defaultValue, ...props }: Props) {
  const [value, setValue] = useState(() => formatPhone(defaultValue ?? ""));
  return (
    <input
      {...props}
      type="tel"
      inputMode="tel"
      value={value}
      onChange={(event) => setValue((previous) => nextPhoneValue(previous, event.target.value))}
    />
  );
}
