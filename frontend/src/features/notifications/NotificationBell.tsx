"use client";

import Link from "next/link";
import { useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { Popover } from "@/components/ui/Popover";
import { Skeleton } from "@/components/ui/Skeleton";
import { useMe } from "@/features/auth/useMe";

import { notificationsCopy as copy } from "./copy";
import { NotificationItem } from "./NotificationItem";
import { useMarkRead, useNotifications, useUnreadCount } from "./useNotifications";

const PREVIEW = 6;

/** Header bell with the unread count; opening it shows the latest ones and marks them read. */
export function NotificationBell() {
  const { me } = useMe();
  const [open, setOpen] = useState(false);
  const unread = useUnreadCount();
  const list = useNotifications(open);
  const markRead = useMarkRead();
  const latest = (list.data?.pages[0]?.results ?? []).slice(0, PREVIEW);
  const unreadShown = latest.filter((item) => !item.is_read).map((item) => item.id);

  function toggle(next: boolean) {
    // Seen in the popover = read: marked when it closes, so the dots stay while reading
    if (!next && unreadShown.length) markRead.mutate(unreadShown);
    setOpen(next);
  }

  if (!me) return null;
  const count = unread.data ?? 0;

  return (
    <Popover
      label={copy.title}
      open={open}
      onOpenChange={toggle}
      align="end"
      trigger={
        <button
          type="button"
          aria-label={copy.bell(count)}
          className="relative inline-flex size-11 items-center justify-center hover:bg-line"
        >
          <Icon name="bell" />
          {count > 0 && (
            <span className="absolute top-2 right-1.5 min-w-4 bg-accent px-1 text-center text-[0.625rem] leading-4 font-medium text-accent-contrast tabular-nums">
              {count > 99 ? "99+" : count}
            </span>
          )}
        </button>
      }
    >
      <div className="flex w-[min(22rem,calc(100vw-2rem))] flex-col">
        {list.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : latest.length ? (
          <ul className="flex flex-col divide-y divide-line">
            {latest.map((notification) => (
              <li key={notification.id}>
                <NotificationItem notification={notification} onNavigate={() => toggle(false)} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-3 py-6 text-sm text-muted">{copy.empty}</p>
        )}
        <Link
          href="/me/notifications"
          onClick={() => toggle(false)}
          className="border-t border-line px-3 py-3 text-sm underline-offset-4 hover:underline"
        >
          {copy.all}
        </Link>
      </div>
    </Popover>
  );
}
