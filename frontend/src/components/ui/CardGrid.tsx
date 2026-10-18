import type { ReactNode } from "react";

/** Catalog grid: 2 / 3 / 4 columns on phone / tablet / desktop, 24 px gap. */
export function CardGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-6 md:grid-cols-3 lg:grid-cols-4">{children}</div>;
}
