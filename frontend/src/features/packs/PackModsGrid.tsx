import Image from "next/image";
import Link from "next/link";

import { Illustration } from "@/components/ui/Illustration";

import { packsCopy } from "./copy";
import { reasonOf, sortItems } from "./items";
import type { PackItem } from "./types";

const copy = packsCopy.detail;

/** The set as an inventory grid: icon, name and why each project is there. */
export function PackModsGrid({ items }: { items: PackItem[] }) {
  const titles = new Map(items.map((item) => [item.project.slug, item.project.title]));
  return (
    <ul className="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-6">
      {sortItems(items).map((item) => {
        const mark = !item.version
          ? copy.noFile
          : reasonOf(item, titles) || (item.env_client === "optional" ? copy.optional : "");
        return (
          <li key={item.project.slug} className="min-w-0">
            <Link href={`/mods/${item.project.slug}`} className="group flex flex-col gap-2">
              <span className="relative aspect-square border border-line bg-surface transition-colors group-hover:border-text">
                {item.project.icon_url ? (
                  <Image
                    src={item.project.icon_url}
                    alt=""
                    fill
                    sizes="128px"
                    className="object-contain p-[18%]"
                  />
                ) : (
                  <span className="flex size-full items-center justify-center">
                    <Illustration name="mods" size={48} />
                  </span>
                )}
              </span>
              <span className="truncate text-sm font-medium group-hover:underline">
                {item.project.title}
              </span>
              {mark && (
                <span
                  className={`-mt-1 line-clamp-2 text-meta ${item.version ? "text-muted" : "text-danger"}`}
                >
                  {mark}
                </span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
