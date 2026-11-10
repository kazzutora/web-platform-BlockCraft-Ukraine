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
    plural(pack.items_count, packsCopy.items),
    downloads ? packsCopy.card.downloads(formatCount(downloads)) : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

type PackCardProps = {
  pack: PackCardData;
  eager?: boolean;
  /** «1.21.1 · Fabric» for the «не для …» mark. */
  gameLabel?: string;
};

export function PackCard({ pack, eager = false, gameLabel = "" }: PackCardProps) {
  const mark =
    pack.fits_my_game === false ? (
      <span className="text-danger">{packsCopy.notForGame(gameLabel)} · </span>
    ) : null;
  return (
    <Card
      href={`/packs/${pack.slug}`}
      title={pack.title}
      meta={
        pack.source ? (
          <>
            {mark}
            {meta(pack)} ·{" "}
            <SourceBadge
              {...pack.source}
              label={packsCopy.detail.source(pack.title, pack.source.name)}
            />
          </>
        ) : (
          <>
            {mark}
            {meta(pack)}
          </>
        )
      }
      action={<SaveToggle kind="pack" id={pack.slug} saved={pack.is_favorited} />}
      cover={<PackCover coverUrl={pack.cover_url} icons={pack.icons} eager={eager} />}
    />
  );
}
