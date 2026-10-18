"use client";

import Link from "next/link";
import { useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Popover } from "@/components/ui/Popover";
import { Skeleton } from "@/components/ui/Skeleton";

import { authCopy } from "./copy";
import { useLogout } from "./useLogout";
import { useMe } from "./useMe";

const copy = authCopy.menu;

/**
 * Header account area. `signedIn` comes from the server (session cookie), so the first
 * render already shows the right thing: «Увійти» for guests, a placeholder for users.
 */
export function AccountMenu({ signedIn }: { signedIn: boolean }) {
  const { me, isLoading } = useMe();
  const logout = useLogout();
  const [open, setOpen] = useState(false);

  if (me) {
    return (
      <Popover
        label={copy.open}
        open={open}
        onOpenChange={setOpen}
        trigger={
          <button
            type="button"
            aria-label={copy.open}
            className="inline-flex size-11 items-center justify-center"
          >
            <Avatar name={me.nickname} src={me.avatar_url} size={32} />
          </button>
        }
      >
        <div className="flex flex-col gap-1">
          <p className="truncate px-2 pb-2 font-medium">{me.nickname}</p>
          <MenuLink href={`/u/${me.nickname}`} onClick={() => setOpen(false)}>
            {copy.profile}
          </MenuLink>
          <MenuLink href="/me/settings" onClick={() => setOpen(false)}>
            {copy.settings}
          </MenuLink>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              void logout();
            }}
            className="flex h-10 items-center px-2 text-left text-sm hover:bg-line"
          >
            {copy.logout}
          </button>
        </div>
      </Popover>
    );
  }

  if (signedIn && isLoading) {
    return <Skeleton className="size-8" />;
  }

  return (
    <ButtonLink href="/login" variant="ghost">
      {copy.login}
    </ButtonLink>
  );
}

function MenuLink({
  href,
  onClick,
  children,
}: {
  href: string;
  onClick: () => void;
  children: string;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="flex h-10 items-center px-2 text-sm hover:bg-line"
    >
      {children}
    </Link>
  );
}
