import Image from "next/image";
import Link from "next/link";

import { StarRating } from "@/components/ui/StarRating";
import { formatDate } from "@/features/mods/format";
import { hitHref } from "@/features/search/hits";
import type { components } from "@/lib/api/schema";

import { activityCopy as copy } from "./copy";

export type ActivityItem = components["schemas"]["ActivityItem"];

/** «Завантажив .mrpack · 1.21.1 · Fabric», «★★★★☆ Топ», «Опис · чекає модератора». */
function meta(item: ActivityItem): string {
  if (item.type === "took") {
    return [copy.actions[item.action ?? ""] ?? "", item.game_version, item.loader]
      .filter(Boolean)
      .join(" · ");
  }
  const status = item.status ? copy.statuses[item.status] : "";
  return [copy.types[item.type], item.type === "translation" ? item.text : "", status]
    .filter(Boolean)
    .join(" · ");
}

/** One row of «Взяв» / «Поділився»: picture, what, when. */
export function ActivityRow({ item }: { item: ActivityItem }) {
  const href = item.kind ? hitHref({ kind: item.kind, id: item.id }) : null;
  return (
    <li className="flex gap-4 border-b border-line py-4">
      <div className="relative size-12 shrink-0 overflow-hidden border border-line bg-surface">
        {item.image && (
          <Image
            src={item.image}
            alt=""
            fill
            sizes="48px"
            unoptimized
            className="object-contain [image-rendering:pixelated]"
          />
        )}
      </div>
      <div className="flex min-w-0 flex-col gap-1">
        {href ? (
          <Link href={href} className="truncate font-medium hover:underline">
            {item.title}
          </Link>
        ) : (
          <span className="truncate font-medium">{item.title}</span>
        )}
        <p className="text-meta text-muted">
          {meta(item)} · {formatDate(item.created_at)}
        </p>
        {item.type === "review" && (
          <div className="flex flex-col gap-1">
            {item.stars ? <StarRating value={item.stars} /> : null}
            {item.text && <p className="line-clamp-2 text-sm">{item.text}</p>}
          </div>
        )}
      </div>
    </li>
  );
}
