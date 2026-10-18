import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type FilterChipProps = {
  active: boolean;
  children: ReactNode;
  className?: string;
} & ({ href: string; onClick?: never } | { href?: never; onClick: () => void });

/**
 * Filter toggle. With `href` it is a link (filters live in the URL),
 * with `onClick` — a toggle button.
 */
export function FilterChip({ active, href, onClick, className, children }: FilterChipProps) {
  const classes = cn(
    "inline-flex h-10 shrink-0 items-center gap-2 border px-4 text-sm whitespace-nowrap transition-colors duration-150",
    active ? "border-text bg-text text-bg" : "border-line text-text hover:border-text",
    className,
  );

  if (href !== undefined) {
    return (
      <Link href={href} aria-current={active ? "true" : undefined} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button type="button" aria-pressed={active} onClick={onClick} className={classes}>
      {children}
    </button>
  );
}
