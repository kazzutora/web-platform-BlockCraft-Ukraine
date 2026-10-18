"use client";

import { SaveButton } from "@/components/ui/SaveButton";

import type { Kind } from "./types";
import { useSave } from "./useSave";

type SaveToggleProps = {
  kind: Kind;
  id: string;
  saved: boolean;
  /** Show the number of saves next to the slot. */
  count?: number;
  className?: string;
};

/** SaveButton wired to /favorites. */
export function SaveToggle({
  kind,
  id,
  saved: initial,
  count: initialCount,
  className,
}: SaveToggleProps) {
  const { saved, count, toggle } = useSave(kind, id, { saved: initial, count: initialCount });
  return <SaveButton saved={saved} onSavedChange={toggle} count={count} className={className} />;
}
