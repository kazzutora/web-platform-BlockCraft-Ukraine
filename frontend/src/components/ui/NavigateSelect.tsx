"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Select } from "./Select";

type NavigateSelectProps = {
  label: string;
  value: string;
  options: Array<{ value: string; label: string; href: string }>;
  placeholder?: string;
};

/** A select whose options are links: choosing one navigates (filters live in the URL). */
export function NavigateSelect({ label, value, options, placeholder }: NavigateSelectProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <div className="w-full sm:w-56">
      <Select
        label={label}
        hideLabel
        value={value}
        placeholder={placeholder}
        options={options}
        aria-busy={pending || undefined}
        onChange={(event) => {
          const option = options.find((item) => item.value === event.target.value);
          const href = option?.href ?? options[0]?.href;
          if (href) startTransition(() => router.push(href, { scroll: false }));
        }}
      />
    </div>
  );
}
