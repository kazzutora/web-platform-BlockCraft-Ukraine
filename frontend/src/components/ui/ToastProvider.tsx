"use client";

import { Toast as ToastPrimitive } from "radix-ui";
import { type ReactNode, createContext, useCallback, useMemo, useState } from "react";

import { cn } from "@/lib/cn";

import { Icon } from "./Icon";

const copy = { close: "Закрити", region: "Сповіщення" };

export type ToastInput = {
  title: string;
  description?: string;
  tone?: "neutral" | "danger";
};

type ToastItem = ToastInput & { id: number };

export const ToastContext = createContext<((toast: ToastInput) => void) | null>(null);

let nextId = 1;

/** Holds toasts for the whole app; show them with `useToast()`. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const show = useCallback((toast: ToastInput) => {
    setToasts((current) => [...current, { ...toast, id: nextId++ }]);
  }, []);
  const remove = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);
  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider swipeDirection="down" duration={5000} label={copy.region}>
        {children}
        {toasts.map((toast) => (
          <ToastPrimitive.Root
            key={toast.id}
            onOpenChange={(open) => !open && remove(toast.id)}
            className={cn(
              "flex items-start gap-4 border bg-surface p-4 text-text data-[state=open]:animate-pop-in",
              toast.tone === "danger" ? "border-danger" : "border-text",
            )}
          >
            <div className="flex flex-1 flex-col gap-1">
              <ToastPrimitive.Title className="text-sm font-medium">
                {toast.title}
              </ToastPrimitive.Title>
              {toast.description && (
                <ToastPrimitive.Description className="text-meta text-muted">
                  {toast.description}
                </ToastPrimitive.Description>
              )}
            </div>
            <ToastPrimitive.Close
              aria-label={copy.close}
              className="-m-2 inline-flex size-10 shrink-0 items-center justify-center hover:bg-line"
            >
              <Icon name="close" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed inset-x-4 bottom-20 z-50 flex flex-col gap-2 outline-none md:inset-x-auto md:right-8 md:bottom-8 md:w-96" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
