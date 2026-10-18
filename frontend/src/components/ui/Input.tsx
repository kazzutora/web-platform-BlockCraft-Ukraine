import { type ComponentProps, useId } from "react";

import { cn } from "@/lib/cn";

import { Field, controlA11y, controlClasses } from "./Field";

type InputProps = ComponentProps<"input"> & {
  label: string;
  hint?: string;
  error?: string;
  hideLabel?: boolean;
};

export function Input({ label, hint, error, hideLabel, id, className, ...props }: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <Field id={inputId} label={label} hint={hint} error={error} hideLabel={hideLabel}>
      <input
        {...controlA11y(inputId, { hint, error })}
        className={cn(controlClasses, "h-12", error ? "border-danger" : "border-line", className)}
        {...props}
      />
    </Field>
  );
}
