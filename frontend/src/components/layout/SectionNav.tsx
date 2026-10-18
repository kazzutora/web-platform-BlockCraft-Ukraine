"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

import { isActive, sections } from "./navigation";

const copy = { label: "Розділи" };

/** Capslock section links; the current section is underlined. */
export function SectionNav({ vertical = false }: { vertical?: boolean }) {
  const pathname = usePathname();
  return (
    <nav aria-label={copy.label}>
      <ul className={cn("flex", vertical ? "flex-col gap-2" : "items-center gap-8")}>
        {sections.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
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
