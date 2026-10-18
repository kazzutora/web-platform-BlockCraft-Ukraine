import { type ComponentProps, useId } from "react";

import { cn } from "@/lib/cn";

import { Field, controlA11y, controlClasses } from "./Field";
import { Icon } from "./Icon";

export type SelectOption = { value: string; label: string };

type SelectProps = Omit<ComponentProps<"select">, "children"> & {
  label: string;
  options: SelectOption[];
  placeholder?: string;
  hint?: string;
  error?: string;
  hideLabel?: boolean;
};

/** Native select: the best experience on phones, styled to match the fields. */
export function Select({
  label,
  options,
  placeholder,
  hint,
  error,
  hideLabel,
  id,
  className,
  ...props
}: SelectProps) {
  const autoId = useId();
  const selectId = id ?? autoId;
  return (
    <Field id={selectId} label={label} hint={hint} error={error} hideLabel={hideLabel}>
      <div className="relative">
        <select
          {...controlA11y(selectId, { hint, error })}
          className={cn(
            controlClasses,
            "h-12 cursor-pointer appearance-none pr-12",
            error ? "border-danger" : "border-line",
            className,
          )}
          {...props}
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Icon
          name="chevron-down"
          className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2"
        />
      </div>
    </Field>
  );
}
