import { cn } from "@/lib/cn";

type SourceBadgeProps = {
  name: string;
  url: string;
  /** Accessible name; the visible text stays «Modrinth ↗». */
  label?: string;
  className?: string;
};

/**
 * «Modrinth ↗»: where the object lives. Sits above a card's stretched link (z-10), so it
 * opens the source instead of the card.
 */
export function SourceBadge({ name, url, label, className }: SourceBadgeProps) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener"
      aria-label={label}
      className={cn(
        "relative z-10 inline-flex items-center gap-0.5 text-meta text-muted underline-offset-4 hover:text-text hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        className,
      )}
    >
      {name}
      <span aria-hidden>↗</span>
    </a>
  );
}
