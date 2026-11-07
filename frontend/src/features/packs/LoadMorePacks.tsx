"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { LoadMore } from "@/components/ui/LoadMore";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { PackCard } from "./PackCard";
import type { CatalogQuery } from "./types";

type LoadMorePacksProps = {
  query: CatalogQuery;
  /** First page that is not rendered yet. */
  startPage: number;
};

/** «Показати ще»: appends the next pages under the server-rendered first one. */
export function LoadMorePacks({ query, startPage }: LoadMorePacksProps) {
  const pages = useInfiniteQuery({
    queryKey: queryKeys.packs.catalog(query),
    initialPageParam: startPage,
    enabled: false,
    queryFn: async ({ pageParam }) => {
      const { data } = await api.GET("/api/v1/packs", {
        params: { query: { ...query, page: pageParam } },
      });
      if (!data) throw new Error("GET /api/v1/packs failed");
      return data;
    },
    getNextPageParam: (last, _all, pageParam) => (last.next ? pageParam + 1 : undefined),
  });

  const loaded = pages.data?.pages ?? [];
  const hasMore = loaded.length === 0 || pages.hasNextPage;

  return (
    <>
      {loaded.length > 0 && (
        <div className="grid grid-cols-2 gap-6 md:grid-cols-3 lg:grid-cols-4">
          {loaded.flatMap((page) =>
            page.results.map((pack) => <PackCard key={pack.slug} pack={pack} />),
          )}
        </div>
      )}
      {hasMore && (
        <LoadMore
          loading={pages.isFetching}
          onClick={() => void (loaded.length ? pages.fetchNextPage() : pages.refetch())}
        />
      )}
    </>
  );
}
