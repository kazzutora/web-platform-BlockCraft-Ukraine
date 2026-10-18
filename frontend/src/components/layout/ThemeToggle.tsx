"use client";

import { useTheme } from "next-themes";

import { Icon } from "@/components/ui/Icon";

const copy = { toggle: "Змінити тему" };

/** Switches between light and dark. Icons follow data-theme via CSS, so there is no hydration flash. */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  return (
    <button
      type="button"
      aria-label={copy.toggle}
      title={copy.toggle}
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className="inline-flex size-11 shrink-0 items-center justify-center text-text transition-colors duration-150 hover:bg-line"
    >
      <Icon name="moon" className="dark:hidden" />
      <Icon name="sun" className="hidden dark:block" />
    </button>
  );
}
