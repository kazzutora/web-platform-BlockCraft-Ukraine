import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Page column: 1200 px max, 16 px gutters on phones, 32 px from tablets. */
export function Container({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("mx-auto w-full max-w-page px-4 md:px-8", className)}>{children}</div>;
}
