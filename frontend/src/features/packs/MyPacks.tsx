"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Card } from "@/components/ui/Card";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api/client";
import { plural } from "@/lib/plural";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import { PackCover } from "./PackCover";

const copy = packsCopy.mine;

/** /me/packs → «Збірки»: drafts lead to the constructor, the rest to their page. */
export function MyPacks() {
  const packs = useQuery({
    queryKey: queryKeys.packs.mine(),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/packs", { params: { query: { page_size: 60 } } });
      if (!data) throw new Error("GET /api/v1/me/packs failed");
      return data;
    },
  });

  const create = (
    <ButtonLink href="/packs/new">
      <Icon name="plus" />
      {packsCopy.create}
    </ButtonLink>
  );

  if (packs.isPending) {
    return (
      <CardGrid>
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="aspect-square w-full" />
        ))}
      </CardGrid>
    );
  }
  if (packs.isError) return <EmptyState illustration="error" title={packsCopy.detail.error} />;
  if (!packs.data.results.length) {
    return <EmptyState illustration="packs" title={copy.empty} action={create} />;
  }

  return (
    <div className="flex flex-col gap-10">
      <div>{create}</div>
      <CardGrid>
        {packs.data.results.map((pack) => (
          <Card
            key={pack.slug}
            href={pack.status === "draft" ? `/packs/${pack.slug}/edit` : `/packs/${pack.slug}`}
            title={pack.title}
            meta={
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <Badge tone={pack.status === "published" ? "neutral" : "accent"}>
                  {packsCopy.builder.status[pack.status]}
                </Badge>
                {plural(pack.items_count, packsCopy.items)}
              </span>
            }
            cover={<PackCover coverUrl={pack.cover_url} icons={pack.icons} />}
          />
        ))}
      </CardGrid>
    </div>
  );
}
