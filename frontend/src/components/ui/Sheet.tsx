"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Icon } from "./Icon";

const copy = { close: "Закрити" };

type SheetProps = {
  title: string;
  /** `bottom` — filters and actions on phones, `right` — the mobile menu. */
  side?: "bottom" | "right";
  trigger?: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
};

/** Panel sliding from the screen edge, for phones. */
export function Sheet({
  title,
  side = "bottom",
  trigger,
  open,
  onOpenChange,
  children,
}: SheetProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-text/40 data-[state=open]:animate-fade-in" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className={cn(
            "fixed z-50 flex flex-col gap-6 overflow-y-auto border-line bg-bg p-6 text-text",
            side === "bottom"
              ? "inset-x-0 bottom-0 max-h-[85dvh] border-t data-[state=open]:animate-slide-up"
              : "inset-y-0 right-0 w-[min(20rem,85vw)] border-l data-[state=open]:animate-slide-left",
          )}
        >
          <div className="flex items-center justify-between gap-4">
            <DialogPrimitive.Title className="caps">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close
              aria-label={copy.close}
              className="-mr-2 inline-flex size-11 items-center justify-center hover:bg-line"
            >
              <Icon name="close" />
            </DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
