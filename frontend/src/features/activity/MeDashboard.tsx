"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import Link from "next/link";

import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { LoadMore } from "@/components/ui/LoadMore";
import { Skeleton } from "@/components/ui/Skeleton";
import { useMe } from "@/features/auth/useMe";
import { gameLabel } from "@/features/game/GameChip";
import { api } from "@/lib/api/client";
import { plural } from "@/lib/plural";
import { queryKeys } from "@/lib/query-keys";

import { ActivityRow } from "./ActivityRow";
import { activityCopy } from "./copy";

const copy = activityCopy.me;
type Section = "took" | "shared";

function useActivity(section: Section) {
  return useInfiniteQuery({
    queryKey: queryKeys.me.activity(section),
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const { data } = await api.GET("/api/v1/me/activity", {
        params: { query: { section, page: pageParam } },
      });
      if (!data) throw new Error("GET /api/v1/me/activity failed");
      return data;
    },
    getNextPageParam: (last) => last.next_page ?? undefined,
  });
}

/** /me: «Моя гра · Взяв · Поділився» — what the player plays, took and gave back. */
export function MeDashboard() {
  const { me } = useMe();
  const took = useActivity("took");
  const shared = useActivity("shared");
  const game = me?.game_profile;
  const label = game
    ? gameLabel({ game_version: game.game_version ?? "", loader: game.loader ?? "" })
    : "";
  const counts = shared.data?.pages[0]?.counts;

  return (
    <div className="flex flex-col gap-16">
      <nav aria-label={copy.title} className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {copy.links.map((link) => (
          <Link key={link.href} href={link.href} className="underline-offset-4 hover:underline">
            {link.label}
          </Link>
        ))}
      </nav>
      <div className="grid gap-12 lg:grid-cols-3">
        <section className="flex flex-col gap-4">
          <h2 className="caps font-sans">{copy.game}</h2>
          <p className="font-display text-h2">{label || "—"}</p>
          {!label && <p className="text-muted">{copy.gameNone}</p>}
          <ButtonLink href="/me/settings" variant="secondary" className="self-start">
            {copy.gameChange}
          </ButtonLink>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="caps font-sans">{copy.took}</h2>
          <Feed query={took} empty={copy.tookEmpty} />
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="caps font-sans">{copy.shared}</h2>
          {counts && (
            <p className="text-meta text-muted">
              {Object.entries(counts)
                .filter(([, count]) => count > 0)
                .map(([key, count]) =>
                  plural(count, activityCopy.counts[key as keyof typeof activityCopy.counts]),
                )
                .join(" · ")}
            </p>
          )}
          <Feed query={shared} empty={copy.sharedEmpty} />
          <ButtonLink href="/share" className="self-start">
            <Icon name="share" />
            {copy.share}
          </ButtonLink>
        </section>
      </div>
    </div>
  );
}

function Feed({ query, empty }: { query: ReturnType<typeof useActivity>; empty: string }) {
  if (query.isPending) return <Skeleton className="h-40 w-full" />;
  if (query.isError) return <EmptyState illustration="error" title={copy.error} />;
  const rows = query.data.pages.flatMap((page) => page.results);
  if (!rows.length) return <p className="text-muted">{empty}</p>;
  return (
    <>
      <ul className="flex flex-col border-t border-line">
        {rows.map((item) => (
          <ActivityRow
            key={`${item.type}-${item.kind}-${item.id}-${item.created_at}`}
            item={item}
          />
        ))}
      </ul>
      {query.hasNextPage && (
        <LoadMore loading={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()} />
      )}
    </>
  );
}
