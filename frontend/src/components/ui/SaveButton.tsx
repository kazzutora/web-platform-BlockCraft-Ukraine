"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";

const copy = { save: "Зберегти" };

type SaveButtonProps = {
  /** Controlled state; omit to let the button keep its own state. */
  saved?: boolean;
  defaultSaved?: boolean;
  onSavedChange?: (saved: boolean) => void;
  count?: number;
  disabled?: boolean;
  className?: string;
};

/** Empty square slot that fills with the accent color when saved (180 ms). */
export function SaveButton({
  saved,
  defaultSaved = false,
  onSavedChange,
  count,
  disabled,
  className,
}: SaveButtonProps) {
  const [ownSaved, setOwnSaved] = useState(defaultSaved);
  const isSaved = saved ?? ownSaved;

  function toggle() {
    const next = !isSaved;
    if (saved === undefined) setOwnSaved(next);
    onSavedChange?.(next);
  }

  return (
    <button
      type="button"
      aria-pressed={isSaved}
      aria-label={copy.save}
      title={copy.save}
      disabled={disabled}
      onClick={toggle}
      className={cn(
        "inline-flex h-11 min-w-11 items-center justify-center gap-2 border border-line bg-surface px-3 text-sm text-text",
        "transition-colors duration-150 hover:border-text disabled:opacity-50",
        className,
      )}
    >
      <span aria-hidden className="relative size-4 border-2 border-text">
        <span
          className={cn(
            "absolute inset-0 bg-accent transition-transform duration-[180ms] ease-out",
            isSaved ? "scale-100" : "scale-0",
          )}
        />
      </span>
      {count !== undefined && <span className="tabular-nums">{count}</span>}
    </button>
  );
}
