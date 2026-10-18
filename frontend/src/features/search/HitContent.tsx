import Image from "next/image";

import { Illustration } from "@/components/ui/Illustration";
import { cn } from "@/lib/cn";

import { hitMeta } from "./hits";
import type { SearchHit } from "./types";

const art = { mod: "mods", skin: "skins", server: "servers", collection: "packs" } as const;

/** Thumbnail, title and one line of metadata (no link: the overlay rows are listbox options). */
export function HitContent({ hit }: { hit: SearchHit }) {
  const pixelated = hit.kind === "skin";
  return (
    <>
      <span className="flex size-12 shrink-0 items-center justify-center overflow-hidden border border-line bg-surface">
        {hit.image ? (
          <Image
            src={hit.image}
            alt=""
            width={48}
            height={48}
            unoptimized={!hit.image.startsWith("https://cdn.modrinth.com")}
            className={cn(
              "size-full",
              pixelated ? "object-contain p-1 [image-rendering:pixelated]" : "object-cover",
            )}
          />
        ) : (
          <Illustration name={art[hit.kind as keyof typeof art] ?? "empty"} size={40} />
        )}
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="truncate font-medium">{hit.title}</span>
        <span className="truncate text-meta text-muted">{hitMeta(hit)}</span>
      </span>
    </>
  );
}
