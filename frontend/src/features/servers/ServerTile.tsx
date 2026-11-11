import Image from "next/image";

import { Card } from "@/components/ui/Card";
import { Illustration } from "@/components/ui/Illustration";
import { SaveToggle } from "@/features/library/SaveToggle";

import { serversCopy } from "./copy";
import type { ServerCard } from "./types";

/** A server as a square card, for grids of mixed content (collections). */
export function ServerTile({ server }: { server: ServerCard }) {
  const live = server.live;
  return (
    <Card
      href={`/servers/${server.slug}`}
      title={server.name}
      meta={[
        server.address,
        live?.is_online ? serversCopy.live.onlineLabel(live.players_online) : "",
      ]
        .filter(Boolean)
        .join(" · ")}
      action={<SaveToggle kind="server" id={server.slug} saved={server.is_favorited} />}
      cover={
        server.banner_url || server.icon_url ? (
          <Image
            src={server.banner_url || server.icon_url}
            alt=""
            fill
            unoptimized
            className="object-cover"
          />
        ) : (
          <div className="flex size-full items-center justify-center">
            <Illustration name="servers" size={96} />
          </div>
        )
      }
    />
  );
}
