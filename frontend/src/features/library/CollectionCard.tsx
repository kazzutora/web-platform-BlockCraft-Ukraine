import Image from "next/image";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Illustration } from "@/components/ui/Illustration";
import { plural } from "@/lib/plural";

import { libraryCopy } from "./copy";
import type { Collection } from "./types";

const copy = libraryCopy.card;

/** 2×2 mosaic of the first items, title and «N елементів · ♥ M». */
export function CollectionCard({
  collection,
  showVisibility = false,
}: {
  collection: Collection;
  showVisibility?: boolean;
}) {
  const meta = [
    plural(collection.items_count, copy.items),
    collection.likes_count ? copy.likes(collection.likes_count) : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card
      href={`/c/${collection.id}`}
      title={collection.title}
      meta={
        showVisibility ? (
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            {meta}
            {collection.visibility !== "public" && (
              <Badge icon={collection.visibility === "private" ? "lock" : "link"}>
                {libraryCopy.visibility[collection.visibility]}
              </Badge>
            )}
          </span>
        ) : (
          meta
        )
      }
      cover={
        collection.preview.length ? (
          <div className="grid size-full grid-cols-2 grid-rows-2 gap-px bg-line">
            {Array.from({ length: 4 }, (_, index) => {
              const src = collection.preview[index];
              return (
                <div key={index} className="flex items-center justify-center bg-surface p-[12%]">
                  {src && (
                    <Image
                      src={src}
                      alt=""
                      width={96}
                      height={96}
                      className="size-full object-contain"
                    />
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex size-full items-center justify-center">
            <Illustration name="packs" size={96} />
          </div>
        )
      }
    />
  );
}
