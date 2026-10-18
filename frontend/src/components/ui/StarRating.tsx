import { cn } from "@/lib/cn";

import { Icon } from "./Icon";

const copy = {
  label: (value: number) => `Оцінка ${value.toLocaleString("uk-UA")} з 5`,
};

type StarRatingProps = {
  value: number;
  /** Number of ratings, shown after the value. */
  count?: number;
  size?: 16 | 24;
  className?: string;
};

/** Read-only rating: five pixel stars, rounded to a whole star. */
export function StarRating({ value, count, size = 16, className }: StarRatingProps) {
  const filled = Math.round(value);
  return (
    <span
      role="img"
      aria-label={copy.label(value)}
      className={cn("inline-flex items-center gap-2 text-meta", className)}
    >
      <span className="inline-flex text-text" aria-hidden>
        {[1, 2, 3, 4, 5].map((star) => (
          <Icon
            key={star}
            name={star <= filled ? "star-filled" : "star"}
            size={size}
            className={star <= filled ? undefined : "text-muted"}
          />
        ))}
      </span>
      <span aria-hidden className="tabular-nums">
        {value.toLocaleString("uk-UA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
        {count !== undefined && <span className="text-muted"> · {count}</span>}
      </span>
    </span>
  );
}
