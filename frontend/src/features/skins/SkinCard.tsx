import Image from "next/image";

import { Card } from "@/components/ui/Card";
import { SaveToggle } from "@/features/library/SaveToggle";
import { formatCount } from "@/features/mods/format";

import { skinsCopy } from "./copy";
import type { SkinCard as SkinCardData } from "./types";

const copy = skinsCopy.card;

/** «Alex_UA · ♥ 12 · ⬇ 340». */
function meta(skin: SkinCardData): string {
  return [
    skin.author.nickname,
    skin.likes_count ? copy.likes(skin.likes_count) : "",
    copy.downloads(formatCount(skin.downloads_count)),
  ]
    .filter(Boolean)
    .join(" · ");
}

/** The 2D front render on the cover (the raw texture until the preview is ready). */
export function SkinCard({ skin, eager = false }: { skin: SkinCardData; eager?: boolean }) {
  return (
    <Card
      href={`/skins/${skin.id}`}
      title={skin.title}
      meta={meta(skin)}
      action={<SaveToggle kind="skin" id={String(skin.id)} saved={skin.is_favorited} />}
      cover={
        <div className="flex size-full items-center justify-center p-[10%]">
          <Image
            src={skin.preview_url ?? skin.texture_url}
            alt=""
            width={128}
            height={skin.preview_url ? 256 : 128}
            unoptimized
            loading={eager ? "eager" : "lazy"}
            className="size-full object-contain [image-rendering:pixelated]"
          />
        </div>
      }
    />
  );
}
