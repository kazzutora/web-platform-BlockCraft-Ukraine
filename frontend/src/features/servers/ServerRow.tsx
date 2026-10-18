import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { SaveToggle } from "@/features/library/SaveToggle";

import { serversCopy } from "./copy";
import { CopyAddress } from "./CopyAddress";
import { OnlineStatus } from "./OnlineStatus";
import type { ServerCard } from "./types";

/** «Виживання, RP · Java · 1.20–1.21 · ★ 4.6». */
function meta(server: ServerCard): string {
  return [
    server.modes.map((mode) => serversCopy.modes[mode]).join(", "),
    serversCopy.editions[server.edition],
    server.versions_label,
    server.rating_count
      ? `★ ${server.rating_avg.toLocaleString("uk-UA", { maximumFractionDigits: 1 })}`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Catalog row: name and modes, live online, the address with «Скопіювати IP». */
export function ServerRow({ server, badge }: { server: ServerCard; badge?: ReactNode }) {
  return (
    <li className="group relative grid gap-4 border-b border-line py-6 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-center md:gap-8">
      <div className="flex min-w-0 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h3 className="font-sans text-card font-medium">
            {/* The whole row opens the server; the buttons stay above the link */}
            <Link href={`/servers/${server.slug}`} className="after:absolute after:inset-0">
              {server.name}
            </Link>
          </h3>
          {server.is_verified && <Badge icon="check">{serversCopy.verified}</Badge>}
          {server.has_whitelist && <Badge>{serversCopy.whitelist}</Badge>}
          {badge}
        </div>
        <p className="text-meta text-muted">{meta(server)}</p>
      </div>
      <OnlineStatus live={server.live} />
      <div className="relative z-10 flex flex-wrap items-center gap-3">
        <code className="font-mono text-sm break-all">{server.address}</code>
        <CopyAddress slug={server.slug} address={server.address} />
        <SaveToggle kind="server" id={server.slug} saved={server.is_favorited} />
      </div>
    </li>
  );
}
