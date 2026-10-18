import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "md" | "lg";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-primary-bg text-primary-fg hover:opacity-85",
  secondary: "border border-text text-text hover:bg-text hover:text-bg",
  ghost: "text-text underline-offset-4 hover:underline",
};

const sizes: Record<ButtonSize, string> = {
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

/** Shared look of buttons and button-like links. */
export function buttonClasses({
  variant = "primary",
  size = "md",
  className,
}: { variant?: ButtonVariant; size?: ButtonSize; className?: string } = {}): string {
  return cn(
    "inline-flex select-none items-center justify-center gap-2 font-medium whitespace-nowrap",
    "transition-[color,background-color,opacity] duration-150",
    "disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50",
    variants[variant],
    sizes[size],
    className,
  );
}
