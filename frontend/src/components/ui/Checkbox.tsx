import { type ComponentProps, useId } from "react";

import { cn } from "@/lib/cn";

type CheckboxProps = Omit<ComponentProps<"input">, "type"> & {
  label: string;
  hint?: string;
};

/** Native checkbox drawn as a square slot that fills with the text color. */
export function Checkbox({ label, hint, id, className, ...props }: CheckboxProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <input
        id={inputId}
        type="checkbox"
        aria-describedby={hint ? `${inputId}-hint` : undefined}
        className={cn(
          "mt-0.5 size-5 shrink-0 cursor-pointer appearance-none border-2 border-text bg-surface p-[3px]",
          // Checked: an inner square (background clipped to the content box)
          "checked:bg-text checked:[background-clip:content-box]",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
        {...props}
      />
      <div className="flex flex-col gap-1">
        <label htmlFor={inputId} className="cursor-pointer text-sm font-medium">
          {label}
        </label>
        {hint && (
          <p id={`${inputId}-hint`} className="text-meta text-muted">
            {hint}
          </p>
        )}
      </div>
    </div>
  );
}
