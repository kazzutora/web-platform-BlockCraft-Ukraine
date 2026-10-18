"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";

export type ChoiceOption<T extends string> = { value: T; label: string };

type BaseProps<T extends string> = {
  label: string;
  options: ChoiceOption<T>[];
  name?: string;
  error?: string;
  hideLabel?: boolean;
};

type SingleProps<T extends string> = BaseProps<T> & {
  multiple?: false;
  value: T | "";
  onChange: (value: T) => void;
};

type MultipleProps<T extends string> = BaseProps<T> & {
  multiple: true;
  value: T[];
  onChange: (value: T[]) => void;
};

/**
 * Chips that behave like radio buttons (one value) or checkboxes (`multiple`).
 * Native inputs underneath: keyboard, screen readers and forms work as usual.
 */
export function ChoiceChips<T extends string>(props: SingleProps<T> | MultipleProps<T>) {
  const { label, options, error, hideLabel = false } = props;
  const groupId = useId();
  const name = props.name ?? groupId;

  function isChecked(value: T) {
    return props.multiple ? props.value.includes(value) : props.value === value;
  }

  function toggle(value: T) {
    if (props.multiple) {
      const next = props.value.includes(value)
        ? props.value.filter((item) => item !== value)
        : [...props.value, value];
      props.onChange(next);
    } else {
      props.onChange(value);
    }
  }

  return (
    <fieldset
      className="flex flex-col gap-3"
      aria-describedby={error ? `${groupId}-error` : undefined}
    >
      <legend className={cn("mb-3 text-sm font-medium", hideLabel && "sr-only")}>{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const checked = isChecked(option.value);
          return (
            <label
              key={option.value}
              className={cn(
                "inline-flex h-10 cursor-pointer items-center border px-4 text-sm whitespace-nowrap transition-colors duration-150",
                "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent",
                checked ? "border-text bg-text text-bg" : "border-line text-text hover:border-text",
              )}
            >
              <input
                type={props.multiple ? "checkbox" : "radio"}
                name={name}
                value={option.value}
                checked={checked}
                onChange={() => toggle(option.value)}
                className="sr-only"
              />
              {option.label}
            </label>
          );
        })}
      </div>
      {error && (
        <p id={`${groupId}-error`} className="text-meta text-danger">
          {error}
        </p>
      )}
    </fieldset>
  );
}
