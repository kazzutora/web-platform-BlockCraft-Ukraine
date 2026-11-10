import { cn } from "@/lib/cn";

export type CompatTone = "ok" | "warning" | "error";

const marks: Record<CompatTone, string> = {
  ok: "bg-accent",
  warning: "bg-warning",
  error: "bg-danger",
};

const texts: Record<CompatTone, string> = {
  ok: "text-text",
  warning: "text-warning",
  error: "text-danger",
};

type CompatStatusProps = {
  tone: CompatTone;
  /** Always present: colour is never the only carrier of meaning. */
  children: React.ReactNode;
  className?: string;
};

/** «■ Сумісно», «■ 2 попередження», «■ Конфлікт»: a square mark and the words. */
export function CompatStatus({ tone, children, className }: CompatStatusProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-meta", texts[tone], className)}>
      <span aria-hidden className={cn("size-2 shrink-0", marks[tone])} />
      {children}
    </span>
  );
}
