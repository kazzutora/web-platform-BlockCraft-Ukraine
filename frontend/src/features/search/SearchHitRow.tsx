import Link from "next/link";

import { HitContent } from "./HitContent";
import { hitHref } from "./hits";
import type { SearchHit } from "./types";

/** A search result on the /search page: the whole row is the link. */
export function SearchHitRow({ hit }: { hit: SearchHit }) {
  return (
    <Link href={hitHref(hit)} className="flex items-center gap-4 px-3 py-2 hover:bg-surface">
      <HitContent hit={hit} />
    </Link>
  );
}
