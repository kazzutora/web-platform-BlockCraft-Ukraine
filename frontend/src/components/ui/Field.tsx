import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  hideLabel?: boolean;
  children: ReactNode;
};

/** Label + control + hint or error. Controls point to the message via aria-describedby. */
export function Field({ id, label, hint, error, hideLabel = false, children }: FieldProps) {
  const message = error ?? hint;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className={cn("text-sm font-medium", hideLabel && "sr-only")}>
        {label}
      </label>
      {children}
      {message && (
        <p id={`${id}-message`} className={cn("text-meta", error ? "text-danger" : "text-muted")}>
          {message}
        </p>
      )}
    </div>
  );
}

export const controlClasses = cn(
  "w-full border bg-surface px-4 text-base text-text placeholder:text-muted",
  "transition-colors duration-150 hover:border-text focus-visible:border-text",
  "disabled:cursor-not-allowed disabled:opacity-50",
);

export function controlA11y(id: string, { hint, error }: { hint?: string; error?: string }) {
  return {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error || hint ? `${id}-message` : undefined,
  } as const;
}
