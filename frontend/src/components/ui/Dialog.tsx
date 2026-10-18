"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Icon } from "./Icon";

const copy = { close: "Закрити" };

type DialogProps = {
  title: string;
  description?: string;
  /** Element that opens the dialog; omit when controlling `open` yourself. */
  trigger?: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: ReactNode;
  /** Actions row; one primary action per dialog. */
  footer?: ReactNode;
};

/** Centered modal on desktop, bottom sheet on phones. */
export function Dialog({
  title,
  description,
  trigger,
  open,
  onOpenChange,
  children,
  footer,
}: DialogProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-text/40 data-[state=open]:animate-fade-in" />
        <DialogPrimitive.Content
          className={cn(
            "fixed z-50 flex max-h-[90dvh] flex-col gap-6 overflow-y-auto border border-line bg-bg p-6 text-text",
            "inset-x-0 bottom-0 border-b-0 data-[state=open]:animate-slide-up",
            "md:inset-x-auto md:top-1/2 md:bottom-auto md:left-1/2 md:w-full md:max-w-lg md:-translate-x-1/2 md:-translate-y-1/2 md:border-b md:p-8 md:data-[state=open]:animate-fade-in",
          )}
          {...(description ? {} : { "aria-describedby": undefined })}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-col gap-2">
              <DialogPrimitive.Title className="text-h2">{title}</DialogPrimitive.Title>
              {description && (
                <DialogPrimitive.Description className="text-muted">
                  {description}
                </DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close
              aria-label={copy.close}
              className="-mt-2 -mr-2 inline-flex size-11 shrink-0 items-center justify-center hover:bg-line"
            >
              <Icon name="close" />
            </DialogPrimitive.Close>
          </div>
          {children}
          {footer && <div className="flex flex-wrap justify-end gap-3">{footer}</div>}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
