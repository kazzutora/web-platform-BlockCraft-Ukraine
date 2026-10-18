import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

import { Icon, type IconName } from "./Icon";

type IconButtonProps = Omit<ComponentProps<"button">, "children"> & {
  icon: IconName;
  /** Required accessible name: the button shows only an icon. */
  label: string;
  variant?: "ghost" | "secondary";
};

export function IconButton({
  icon,
  label,
  variant = "ghost",
  className,
  type = "button",
  ...props
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-11 shrink-0 items-center justify-center text-text transition-colors duration-150",
        "disabled:pointer-events-none disabled:opacity-50",
        variant === "secondary" ? "border border-line hover:border-text" : "hover:bg-line",
        className,
      )}
      {...props}
    >
      <Icon name={icon} />
    </button>
  );
}
