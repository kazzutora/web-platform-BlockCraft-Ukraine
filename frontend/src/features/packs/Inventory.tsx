"use client";

import Image from "next/image";
import Link from "next/link";

import { Checkbox } from "@/components/ui/Checkbox";
import { EmptyState } from "@/components/ui/EmptyState";
import { IconButton } from "@/components/ui/IconButton";
import { Illustration } from "@/components/ui/Illustration";
import { cn } from "@/lib/cn";

import { packsCopy } from "./copy";
import { reasonOf, sortItems } from "./items";
import type { PackItem } from "./types";

const copy = packsCopy.builder;

type InventoryProps = {
  items: PackItem[];
  /** Projects being added right now: the server is still resolving the set. */
  pending: Set<string>;
  onRemove: (project: string) => void;
  onOptionalChange: (project: string, optional: boolean) => void;
};

/** Right half of the constructor: the author's picks, then what they pulled in and why. */
export function Inventory({ items, pending, onRemove, onOptionalChange }: InventoryProps) {
  const sorted = sortItems(items);
  const titles = new Map(items.map((item) => [item.project.slug, item.project.title]));
  return (
    <section aria-labelledby="inventory" className="flex min-w-0 flex-col gap-5">
      <h2 id="inventory" className="text-h2">
        {copy.inventory} <span className="text-muted tabular-nums">· {items.length}</span>
      </h2>
      {sorted.length ? (
        <ul className="flex flex-col divide-y divide-line border-y border-line">
          {sorted.map((item) => {
            const saving = pending.has(item.project.slug);
            const picked = item.reason === "requested";
            const why = reasonOf(item, titles);
            return (
              <li
                key={item.project.slug}
                aria-busy={saving || undefined}
                className={cn("flex items-start gap-4 py-3", saving && "opacity-60")}
              >
                <span className="relative size-12 shrink-0 border border-line bg-surface">
                  {item.project.icon_url ? (
                    <Image
                      src={item.project.icon_url}
                      alt=""
                      fill
                      sizes="48px"
                      className="object-contain p-1"
                    />
                  ) : (
                    <Illustration name="mods" size={44} />
                  )}
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <div className="flex min-w-0 flex-col gap-1">
                    <Link
                      href={`/mods/${item.project.slug}`}
                      className="truncate font-medium hover:underline"
                    >
                      {item.project.title}
                    </Link>
                    <span className="flex flex-wrap items-center gap-x-2 text-meta text-muted">
                      {item.version ? (
                        <span className="truncate font-mono">{item.version.version_number}</span>
                      ) : (
                        !saving && <span className="text-danger">{packsCopy.detail.noFile}</span>
                      )}
                      {why && <span>· {why}</span>}
                    </span>
                  </div>
                  {!saving && (
                    <Checkbox
                      label={copy.optional}
                      checked={item.env_client === "optional"}
                      onChange={(event) =>
                        onOptionalChange(item.project.slug, event.target.checked)
                      }
                    />
                  )}
                </div>
                {picked && (
                  <IconButton
                    icon="trash"
                    label={copy.remove(item.project.title)}
                    disabled={saving}
                    onClick={() => onRemove(item.project.slug)}
                  />
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <EmptyState title={copy.emptyInventory} illustration="packs" />
      )}
    </section>
  );
}
