import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { getServerClient } from "@/lib/api/server-client";

import { searchCopy as copy } from "./copy";
import { SearchHitRow } from "./SearchHitRow";
import { type SearchKind, searchKinds } from "./types";

type Query = { q: string; kind?: SearchKind; page?: number; mine?: boolean };

export function searchHref({ q, kind, page, mine }: Query): string {
  const params = new URLSearchParams({ q });
  if (kind) params.set("kind", kind);
  if (mine) params.set("mine", "1");
  if (page && page > 1) params.set("page", String(page));
  return `/search?${params}`;
}

type SearchResultsProps = {
  q: string;
  kind?: SearchKind;
  page: number;
  /** Only mods and packs that fit «Моя гра». */
  mine: boolean;
  /** «1.21.1 · Fabric»; empty while «Моя гра» is not chosen (no toggle then). */
  gameLabel: string;
};

/** /search: all kinds in groups of five, or one kind page by page. */
export async function SearchResults({ q, kind, page, mine, gameLabel }: SearchResultsProps) {
  const onlyMine = mine && Boolean(gameLabel);
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/search", {
    params: { query: { q, page, ...(kind ? { kind } : {}), ...(onlyMine ? { mine: true } : {}) } },
  });
  const groups = data?.groups ?? [];
  const found = groups.some((group) => group.results.length);

  return (
    <div className="flex flex-col gap-6">
      <FilterRow label={copy.tabsLabel}>
        <FilterChip href={searchHref({ q, mine: onlyMine })} active={!kind}>
          {copy.allKinds}
        </FilterChip>
        {searchKinds.map((name) => (
          <FilterChip
            key={name}
            href={searchHref({ q, kind: name, mine: onlyMine })}
            active={kind === name}
          >
            {copy.kinds[name]}
          </FilterChip>
        ))}
      </FilterRow>
      {gameLabel && (
        <FilterRow label={copy.mineLabel}>
          <FilterChip href={searchHref({ q, kind, mine: !onlyMine })} active={onlyMine}>
            {copy.onlyMine(gameLabel)}
          </FilterChip>
        </FilterRow>
      )}

      <div className="mt-4 flex flex-col gap-10">
        {!data ? (
          <EmptyState illustration="error" title={copy.error} />
        ) : !found ? (
          <EmptyState illustration="void" title={copy.empty(q)} />
        ) : (
          groups
            .filter((group) => group.results.length)
            .map((group) => (
              <section key={group.kind} className="flex flex-col gap-3">
                <h2 className="caps font-sans text-muted">
                  {copy.kinds[group.kind as SearchKind]} · {group.total}
                </h2>
                <ul className="flex flex-col divide-y divide-line border-y border-line">
                  {group.results.map((hit) => (
                    <li key={`${hit.kind}-${hit.id}`}>
                      <SearchHitRow hit={hit} gameLabel={gameLabel} />
                    </li>
                  ))}
                </ul>
                {!kind && group.total > group.results.length && (
                  <ButtonLink
                    href={searchHref({ q, kind: group.kind as SearchKind, mine: onlyMine })}
                    variant="ghost"
                    className="self-start px-0"
                  >
                    {copy.more(group.total)}
                  </ButtonLink>
                )}
                {kind && group.next_page && (
                  <ButtonLink
                    href={searchHref({ q, kind, page: group.next_page, mine: onlyMine })}
                    variant="secondary"
                    className="self-start"
                  >
                    {copy.next}
                  </ButtonLink>
                )}
              </section>
            ))
        )}
      </div>
    </div>
  );
}
