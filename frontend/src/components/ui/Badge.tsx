import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Icon, type IconName } from "./Icon";

type BadgeProps = {
  tone?: "neutral" | "accent";
  icon?: IconName;
  children: ReactNode;
};

/** Small status mark: «Перевірено», «Новий», counters. */
export function Badge({ tone = "neutral", icon, children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1 border px-2 text-meta font-medium",
        tone === "accent"
          ? "border-accent bg-accent text-accent-contrast"
          : "border-line text-text",
      )}
    >
      {icon && <Icon name={icon} size={16} />}
      {children}
    </span>
  );
}
