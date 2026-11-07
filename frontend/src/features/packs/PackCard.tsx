import { Card } from "@/components/ui/Card";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { SaveToggle } from "@/features/library/SaveToggle";
import { formatCount } from "@/features/mods/format";
import { plural } from "@/lib/plural";

import { packsCopy } from "./copy";
import { PackCover } from "./PackCover";
import type { PackCard as PackCardData } from "./types";

/** «26.3 · Fabric · 51 мод · ⬇ 12 тис.». */
function meta(pack: PackCardData): string {
  const downloads = pack.downloads_count + pack.modrinth_downloads;
  return [
    pack.game_version,
    packsCopy.loaders[pack.loader],
    plural(pack.mods_count, packsCopy.mods),
    downloads ? packsCopy.card.downloads(formatCount(downloads)) : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

export function PackCard({ pack, eager = false }: { pack: PackCardData; eager?: boolean }) {
  return (
    <Card
      href={`/packs/${pack.slug}`}
      title={pack.title}
      meta={
        pack.source ? (
          <>
            {meta(pack)} ·{" "}
            <SourceBadge
              {...pack.source}
              label={packsCopy.detail.source(pack.title, pack.source.name)}
            />
          </>
        ) : (
          meta(pack)
        )
      }
      action={<SaveToggle kind="pack" id={pack.slug} saved={pack.is_favorited} />}
      cover={<PackCover coverUrl={pack.cover_url} icons={pack.icons} eager={eager} />}
    />
  );
}
