"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { LoadMore } from "@/components/ui/LoadMore";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { ServerRow } from "./ServerRow";
import type { CatalogQuery } from "./types";

type LoadMoreServersProps = {
  query: CatalogQuery;
  /** First page that is not rendered yet. */
  startPage: number;
};

/** «Показати ще»: appends the next pages under the server-rendered first one. */
export function LoadMoreServers({ query, startPage }: LoadMoreServersProps) {
  const pages = useInfiniteQuery({
    queryKey: queryKeys.servers.catalog(query),
    initialPageParam: startPage,
    enabled: false,
    queryFn: async ({ pageParam }) => {
      const { data } = await api.GET("/api/v1/servers", {
        params: { query: { ...query, page: pageParam } },
      });
      if (!data) throw new Error("GET /api/v1/servers failed");
      return data;
    },
    getNextPageParam: (last, _all, pageParam) => (last.next ? pageParam + 1 : undefined),
  });

  const loaded = pages.data?.pages ?? [];
  const hasMore = loaded.length === 0 || pages.hasNextPage;

  return (
    <>
      {loaded.length > 0 && (
        <ul className="-mt-10 flex flex-col md:-mt-16">
          {loaded.flatMap((page) =>
            page.results.map((server) => <ServerRow key={server.slug} server={server} />),
          )}
        </ul>
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
