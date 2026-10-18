"use client";

import { useId, useState } from "react";

import { Icon } from "./Icon";

const copy = {
  star: (value: number) => `${value} з 5`,
};

type StarRatingInputProps = {
  label: string;
  name: string;
  value?: number;
  defaultValue?: number;
  onValueChange?: (value: number) => void;
};

/** Rating picker built on native radio buttons: arrows, Tab and screen readers work out of the box. */
export function StarRatingInput({
  label,
  name,
  value,
  defaultValue = 0,
  onValueChange,
}: StarRatingInputProps) {
  const [ownValue, setOwnValue] = useState(defaultValue);
  const current = value ?? ownValue;
  const [hovered, setHovered] = useState(0);
  const groupId = useId();
  const shown = hovered || current;

  function select(next: number) {
    if (value === undefined) setOwnValue(next);
    onValueChange?.(next);
  }

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{label}</legend>
      <div className="flex" onMouseLeave={() => setHovered(0)}>
        {[1, 2, 3, 4, 5].map((star) => {
          const id = `${groupId}-${star}`;
          return (
            <label
              key={star}
              htmlFor={id}
              onMouseEnter={() => setHovered(star)}
              className="inline-flex size-11 cursor-pointer items-center justify-center has-focus-visible:outline-2 has-focus-visible:outline-accent"
            >
              <input
                id={id}
                type="radio"
                name={name}
                value={star}
                checked={current === star}
                onChange={() => select(star)}
                className="sr-only"
              />
              <Icon
                name={star <= shown ? "star-filled" : "star"}
                className={star <= shown ? "text-text" : "text-muted"}
              />
              <span className="sr-only">{copy.star(star)}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
