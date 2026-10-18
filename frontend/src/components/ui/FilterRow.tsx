import type { ReactNode } from "react";

/** Horizontal row of filter chips: scrolls on phones instead of a sidebar. */
export function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      role="group"
      aria-label={label}
      className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:overflow-visible md:px-0"
    >
      {children}
    </div>
  );
}
