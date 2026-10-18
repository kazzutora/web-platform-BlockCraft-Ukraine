import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type ChipTone = "neutral" | "mods" | "packs" | "skins" | "servers" | "moments";

const markers: Record<ChipTone, string> = {
  neutral: "bg-muted",
  mods: "bg-tag-mods",
  packs: "bg-tag-packs",
  skins: "bg-tag-skins",
  servers: "bg-tag-servers",
  moments: "bg-tag-moments",
};

/**
 * Static label, e.g. a section mark. The section color is a square marker,
 * the text keeps the main color for contrast.
 */
export function Chip({ tone = "neutral", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span className="caps inline-flex h-7 items-center gap-2 border border-line px-2 text-text">
      <span aria-hidden className={cn("size-2", markers[tone])} />
      {children}
    </span>
  );
}
