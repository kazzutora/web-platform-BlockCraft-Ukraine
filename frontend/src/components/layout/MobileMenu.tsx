"use client";

import Link from "next/link";
import { useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { IconButton } from "@/components/ui/IconButton";
import { Sheet } from "@/components/ui/Sheet";
import { authCopy } from "@/features/auth/copy";
import { useLogout } from "@/features/auth/useLogout";
import { useMe } from "@/features/auth/useMe";

import { SectionNav } from "./SectionNav";
import { ThemeToggle } from "./ThemeToggle";

const copy = { ...authCopy.menu, open: "Меню", title: "Меню", theme: "Тема" };

/** Phone menu: sections, account, theme in a sheet from the right. Links close it. */
export function MobileMenu() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  const { me } = useMe();
  const logout = useLogout();

  return (
    <Sheet
      title={copy.title}
      side="right"
      open={open}
      onOpenChange={setOpen}
      trigger={<IconButton icon="menu" label={copy.open} />}
    >
      <SectionNav vertical onNavigate={close} />
      {me && (
        <div className="flex flex-col gap-1 border-t border-line pt-4">
          <p className="flex items-center gap-3 pb-2 font-medium">
            <Avatar name={me.nickname} src={me.avatar_url} size={32} />
            {me.nickname}
          </p>
          <Link
            href={`/u/${me.nickname}`}
            onClick={close}
            className="flex h-11 items-center text-sm"
          >
            {copy.profile}
          </Link>
          <Link href="/me/settings" onClick={close} className="flex h-11 items-center text-sm">
            {copy.settings}
          </Link>
          <button
            type="button"
            onClick={() => {
              close();
              void logout();
            }}
            className="flex h-11 items-center text-left text-sm"
          >
            {copy.logout}
          </button>
        </div>
      )}
      <div className="flex items-center justify-between border-t border-line pt-4">
        <span className="caps text-muted">{copy.theme}</span>
        <ThemeToggle />
      </div>
      {!me && (
        <ButtonLink href="/login" variant="primary" size="lg" onClick={close}>
          {copy.login}
        </ButtonLink>
      )}
    </Sheet>
  );
}
