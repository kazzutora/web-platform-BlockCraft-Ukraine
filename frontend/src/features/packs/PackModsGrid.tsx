import Image from "next/image";
import Link from "next/link";

import { Illustration } from "@/components/ui/Illustration";

import { packsCopy } from "./copy";
import type { PackItem } from "./types";

const copy = packsCopy.detail;

/** Mods as an inventory grid: icon, name and a mark for dependencies and optional ones. */
export function PackModsGrid({ items }: { items: PackItem[] }) {
  // The author's picks first, the libraries they pulled in after
  const sorted = [...items].sort(
    (a, b) => Number(a.added_as_dependency) - Number(b.added_as_dependency),
  );
  return (
    <ul className="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-6">
      {sorted.map((item) => {
        const mark = !item.version
          ? copy.noFile
          : item.added_as_dependency
            ? copy.dependency
            : !item.is_required
              ? copy.optional
              : "";
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
              {mark && <span className="-mt-1 text-meta text-muted">{mark}</span>}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
