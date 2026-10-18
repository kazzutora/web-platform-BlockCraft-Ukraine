"use client";

import { Tabs as TabsPrimitive } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type TabItem = {
  value: string;
  label: string;
  content: ReactNode;
};

type TabsProps = {
  items: TabItem[];
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  /** Accessible name of the tab list. */
  label: string;
  className?: string;
};

/** Capslock tabs, the active one is underlined with a 2 px line. Arrow keys move between tabs. */
export function Tabs({ items, defaultValue, value, onValueChange, label, className }: TabsProps) {
  return (
    <TabsPrimitive.Root
      defaultValue={defaultValue ?? items[0]?.value}
      value={value}
      onValueChange={onValueChange}
      className={cn("flex flex-col gap-8", className)}
    >
      <TabsPrimitive.List
        aria-label={label}
        className="no-scrollbar -mx-4 flex gap-8 overflow-x-auto border-b border-line px-4 md:mx-0 md:px-0"
      >
        {items.map((item) => (
          <TabsPrimitive.Trigger
            key={item.value}
            value={item.value}
            className={cn(
              "caps -mb-px flex h-12 shrink-0 items-center border-b-2 border-transparent text-muted transition-colors",
              "hover:text-text data-[state=active]:border-text data-[state=active]:text-text",
            )}
          >
            {item.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {items.map((item) => (
        <TabsPrimitive.Content key={item.value} value={item.value}>
          {item.content}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}
