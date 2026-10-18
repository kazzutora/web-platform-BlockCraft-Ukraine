import Link from "next/link";

import { cn } from "@/lib/cn";

import { describe } from "./format";
import type { Notification } from "./types";

// A fixed zone: the server render and the browser print the same date
const formatter = new Intl.DateTimeFormat("uk-UA", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Kyiv",
});

/** One notification: a green square while unread, the text, the time; links to the object. */
export function NotificationItem({
  notification,
  onNavigate,
}: {
  notification: Notification;
  onNavigate?: () => void;
}) {
  const { text, href } = describe(notification);
  const body = (
    <>
      <span
        aria-hidden
        className={cn(
          "mt-1.5 size-2 shrink-0",
          notification.is_read ? "bg-transparent" : "bg-accent",
        )}
      />
      <span className="flex min-w-0 flex-col gap-1">
        <span className="text-sm break-words">{text}</span>
        <time dateTime={notification.created_at} className="text-meta text-muted">
          {formatter.format(new Date(notification.created_at))}
        </time>
      </span>
    </>
  );
  const classes = "flex gap-3 px-3 py-3";
  return href ? (
    <Link href={href} onClick={onNavigate} className={cn(classes, "hover:bg-surface")}>
      {body}
    </Link>
  ) : (
    <div className={classes}>{body}</div>
  );
}
