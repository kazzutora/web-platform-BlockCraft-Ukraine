import { type ComponentProps, useId } from "react";

import { cn } from "@/lib/cn";

import { Field, controlA11y, controlClasses } from "./Field";

type TextareaProps = ComponentProps<"textarea"> & {
  label: string;
  hint?: string;
  error?: string;
  hideLabel?: boolean;
};

export function Textarea({
  label,
  hint,
  error,
  hideLabel,
  id,
  className,
  rows = 4,
  ...props
}: TextareaProps) {
  const autoId = useId();
  const textareaId = id ?? autoId;
  return (
    <Field id={textareaId} label={label} hint={hint} error={error} hideLabel={hideLabel}>
      <textarea
        rows={rows}
        {...controlA11y(textareaId, { hint, error })}
        className={cn(
          controlClasses,
          "resize-y py-3",
          error ? "border-danger" : "border-line",
          className,
        )}
        {...props}
      />
    </Field>
  );
}
