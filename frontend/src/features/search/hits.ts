import { loaderName, mainLoadersOf } from "@/features/mods/format";
import { serversCopy } from "@/features/servers/copy";
import { plural } from "@/lib/plural";

import { searchCopy } from "./copy";
import type { SearchHit } from "./types";

/** Where a hit leads. */
export function hitHref(hit: Pick<SearchHit, "kind" | "id">): string {
  const id = encodeURIComponent(hit.id);
  switch (hit.kind) {
    case "mod":
      return `/mods/${id}`;
    case "skin":
      return `/skins/${id}`;
    case "server":
      return `/servers/${id}`;
    default:
      return `/c/${id}`;
  }
}

/** One line under the title: «Мод · 26.3 · Fabric», «Скін · Mavka», «play.sich.ua · Виживання». */
export function hitMeta(hit: SearchHit): string {
  const kinds = searchCopy.kind;
  switch (hit.kind) {
    case "mod": {
      const type = (hit.project_type ?? "mod") as keyof typeof kinds;
      const loaders = hit.project_type === "mod" ? mainLoadersOf(hit.loaders).slice(0, 2) : [];
      return [kinds[type] ?? kinds.mod, hit.latest_game_version, loaders.map(loaderName).join(", ")]
        .filter(Boolean)
        .join(" · ");
    }
    case "skin":
      return [kinds.skin, hit.author].filter(Boolean).join(" · ");
    case "server":
      return [
        hit.address,
        hit.modes
          .slice(0, 2)
          .map((mode) => serversCopy.modes[mode as keyof typeof serversCopy.modes] ?? mode)
          .join(", "),
      ]
        .filter(Boolean)
        .join(" · ");
    default:
      return [
        kinds.collection,
        hit.items_count !== null && hit.items_count !== undefined
          ? plural(hit.items_count, searchCopy.items)
          : "",
      ]
        .filter(Boolean)
        .join(" · ");
  }
}
