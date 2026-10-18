import Link from "next/link";

import { cn } from "@/lib/cn";

import { isActive, sections } from "./navigation";

const copy = { label: "Розділи" };

type SectionLinksProps = {
  /** Current path; null while it is unknown (static shell before streaming). */
  pathname?: string | null;
  vertical?: boolean;
  onNavigate?: () => void;
};

/** Capslock section links; the current section is underlined. */
export function SectionLinks({ pathname = null, vertical = false, onNavigate }: SectionLinksProps) {
  return (
    <nav aria-label={copy.label}>
      <ul className={cn("flex", vertical ? "flex-col gap-2" : "items-center gap-8")}>
        {sections.map((item) => {
          const active = pathname !== null && isActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "caps inline-flex items-center border-b-2 transition-colors",
                  vertical ? "h-12 text-sm" : "h-16",
                  active
                    ? "border-text text-text"
                    : "border-transparent text-muted hover:text-text",
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
