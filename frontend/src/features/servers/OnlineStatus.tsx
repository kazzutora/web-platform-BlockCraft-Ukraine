import { cn } from "@/lib/cn";

import { serversCopy } from "./copy";
import type { LiveStatus } from "./types";

const copy = serversCopy.live;

/** Green square with «12 / 100», grey «Офлайн», or «Перевіряємо…» before the first ping. */
export function OnlineStatus({ live, className }: { live: LiveStatus | null; className?: string }) {
  const state = live === null ? "unknown" : live.is_online ? "online" : "offline";
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm tabular-nums", className)}>
      <span
        aria-hidden
        className={cn("size-2.5", state === "online" ? "bg-accent" : "border border-muted")}
      />
      {live?.is_online
        ? copy.online(live.players_online, live.players_max)
        : state === "offline"
          ? copy.offline
          : copy.unknown}
    </span>
  );
}
