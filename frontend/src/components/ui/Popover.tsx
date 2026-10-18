"use client";

import { Popover as PopoverPrimitive } from "radix-ui";
import type { ReactNode } from "react";

type PopoverProps = {
  trigger: ReactNode;
  /** Accessible name of the popover content. */
  label: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  align?: "start" | "center" | "end";
  children: ReactNode;
};

export function Popover({
  trigger,
  label,
  open,
  onOpenChange,
  align = "end",
  children,
}: PopoverProps) {
  return (
    <PopoverPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <PopoverPrimitive.Trigger asChild>{trigger}</PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          aria-label={label}
          align={align}
          sideOffset={8}
          collisionPadding={16}
          className="z-50 w-72 max-w-[calc(100vw-2rem)] border border-line bg-surface p-4 text-text data-[state=open]:animate-pop-in"
        >
          {children}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
