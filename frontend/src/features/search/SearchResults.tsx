import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { getServerClient } from "@/lib/api/server-client";

import { searchCopy as copy } from "./copy";
import { SearchHitRow } from "./SearchHitRow";
import { type SearchKind, searchKinds } from "./types";

function href(q: string, kind?: SearchKind, page?: number): string {
  const params = new URLSearchParams({ q });
  if (kind) params.set("kind", kind);
  if (page && page > 1) params.set("page", String(page));
  return `/search?${params}`;
}

type SearchResultsProps = { q: string; kind?: SearchKind; page: number };

/** /search: all kinds in groups of five, or one kind page by page. */
export async function SearchResults({ q, kind, page }: SearchResultsProps) {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/search", {
    params: { query: { q, page, ...(kind ? { kind } : {}) } },
  });
  const groups = data?.groups ?? [];
  const found = groups.some((group) => group.results.length);

  return (
    <div className="flex flex-col gap-10">
      <FilterRow label={copy.tabsLabel}>
        <FilterChip href={href(q)} active={!kind}>
          {copy.allKinds}
        </FilterChip>
        {searchKinds.map((name) => (
          <FilterChip key={name} href={href(q, name)} active={kind === name}>
            {copy.kinds[name]}
          </FilterChip>
        ))}
      </FilterRow>

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
                    <SearchHitRow hit={hit} />
                  </li>
                ))}
              </ul>
              {!kind && group.total > group.results.length && (
                <ButtonLink
                  href={href(q, group.kind as SearchKind)}
                  variant="ghost"
                  className="self-start px-0"
                >
                  {copy.more(group.total)}
                </ButtonLink>
              )}
              {kind && group.next_page && (
                <ButtonLink
                  href={href(q, kind, group.next_page)}
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
  );
}
