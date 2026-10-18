import { cn } from "@/lib/cn";

/** Loading placeholder: a pulsing rectangle in the line color. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse bg-line", className)} />;
}
