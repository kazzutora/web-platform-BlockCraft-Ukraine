"use client";

import Image from "next/image";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Checkbox } from "@/components/ui/Checkbox";
import { EmptyState } from "@/components/ui/EmptyState";
import { IconButton } from "@/components/ui/IconButton";
import { Illustration } from "@/components/ui/Illustration";
import { cn } from "@/lib/cn";

import { packsCopy } from "./copy";
import type { PackItem } from "./types";

const copy = packsCopy.builder;

type InventoryProps = {
  items: PackItem[];
  /** Projects being added right now: the server is still picking their files. */
  pending: Set<string>;
  onRemove: (project: string) => void;
  onRequiredChange: (project: string, required: boolean) => void;
};

/** Right half of the constructor: what is in the pack; dependencies are marked and listed last. */
export function Inventory({ items, pending, onRemove, onRequiredChange }: InventoryProps) {
  const sorted = [...items].sort(
    (a, b) => Number(a.added_as_dependency) - Number(b.added_as_dependency),
  );
  return (
    <section aria-labelledby="inventory" className="flex min-w-0 flex-col gap-5">
      <h2 id="inventory" className="text-h2">
        {copy.inventory} <span className="text-muted tabular-nums">· {items.length}</span>
      </h2>
      {sorted.length ? (
        <ul className="flex flex-col divide-y divide-line border-y border-line">
          {sorted.map((item) => {
            const saving = pending.has(item.project.slug);
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
                    <span className="flex flex-wrap items-center gap-2 text-meta text-muted">
                      {item.version ? (
                        <span className="truncate">{item.version.version_number}</span>
                      ) : (
                        !saving && <span className="text-danger">{packsCopy.detail.noFile}</span>
                      )}
                      {item.added_as_dependency && <Badge>{packsCopy.detail.dependency}</Badge>}
                    </span>
                  </div>
                  {!saving && (
                    <Checkbox
                      label={copy.required}
                      checked={item.is_required}
                      onChange={(event) =>
                        onRequiredChange(item.project.slug, event.target.checked)
                      }
                    />
                  )}
                </div>
                <IconButton
                  icon="trash"
                  label={copy.remove(item.project.title)}
                  disabled={saving}
                  onClick={() => onRemove(item.project.slug)}
                />
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
