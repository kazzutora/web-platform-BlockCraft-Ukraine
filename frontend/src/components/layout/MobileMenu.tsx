"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";

import { ButtonLink } from "@/components/ui/ButtonLink";
import { IconButton } from "@/components/ui/IconButton";
import { Sheet } from "@/components/ui/Sheet";

import { SectionNav } from "./SectionNav";
import { ThemeToggle } from "./ThemeToggle";

const copy = { open: "Меню", title: "Меню", login: "Увійти", theme: "Тема" };

/** Phone menu: sections, theme and sign-in in a sheet from the right. Closes on navigation. */
export function MobileMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const [lastPathname, setLastPathname] = useState(pathname);
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setOpen(false);
  }

  return (
    <Sheet
      title={copy.title}
      side="right"
      open={open}
      onOpenChange={setOpen}
      trigger={<IconButton icon="menu" label={copy.open} />}
    >
      <SectionNav vertical />
      <div className="flex items-center justify-between border-t border-line pt-4">
        <span className="caps text-muted">{copy.theme}</span>
        <ThemeToggle />
      </div>
      <ButtonLink href="/login" variant="primary" size="lg">
        {copy.login}
      </ButtonLink>
    </Sheet>
  );
}
