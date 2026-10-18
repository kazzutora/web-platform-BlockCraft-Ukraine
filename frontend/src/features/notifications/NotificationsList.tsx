"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

import { notificationsCopy as copy } from "./copy";
import { NotificationItem } from "./NotificationItem";
import { useMarkRead, useNotifications } from "./useNotifications";

/** /me/notifications: everything, newest first, 20 per page. */
export function NotificationsList() {
  const list = useNotifications();
  const markRead = useMarkRead();

  if (list.isPending) return <Skeleton className="h-64 w-full" />;
  if (list.isError) return <EmptyState illustration="error" title={copy.error} />;
  const items = list.data.pages.flatMap((page) => page.results);
  if (!items.length) return <EmptyState illustration="void" title={copy.empty} />;
  const unread = list.data.pages[0]?.unread_count ?? 0;

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      {unread > 0 && (
        <Button
          variant="secondary"
          className="self-start"
          loading={markRead.isPending}
          onClick={() => markRead.mutate(undefined)}
        >
          {copy.markAll}
        </Button>
      )}
      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {items.map((notification) => (
          <li key={notification.id}>
            <NotificationItem notification={notification} />
          </li>
        ))}
      </ul>
      {list.hasNextPage && (
        <Button
          variant="secondary"
          className="self-center"
          loading={list.isFetchingNextPage}
          onClick={() => void list.fetchNextPage()}
        >
          {copy.more}
        </Button>
      )}
    </div>
  );
}
