"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";

import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Card } from "@/components/ui/Card";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { skinsCopy } from "./copy";

const copy = skinsCopy.mine;

/** /me/works: every skin of mine with its moderation status. */
export function MySkins() {
  const skins = useQuery({
    queryKey: queryKeys.skins.mine(),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/skins", { params: { query: { page_size: 60 } } });
      if (!data) throw new Error("GET /api/v1/me/skins failed");
      return data;
    },
  });

  const upload = (
    <ButtonLink href="/skins/new">
      <Icon name="upload" />
      {skinsCopy.upload}
    </ButtonLink>
  );

  if (skins.isPending) {
    return (
      <CardGrid>
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="aspect-square w-full" />
        ))}
      </CardGrid>
    );
  }
  if (skins.isError) return <EmptyState illustration="error" title={skinsCopy.detail.error} />;
  if (!skins.data.results.length) {
    return <EmptyState illustration="skins" title={copy.empty} action={upload} />;
  }

  return (
    <div className="flex flex-col gap-10">
      <div>{upload}</div>
      <CardGrid>
        {skins.data.results.map((skin) => (
          <Card
            key={skin.id}
            href={`/skins/${skin.id}`}
            title={skin.title}
            meta={
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <Badge tone={skin.status === "published" ? "neutral" : "accent"}>
                  {copy.status[skin.status]}
                </Badge>
                {skin.is_current && skinsCopy.detail.isCurrent}
              </span>
            }
            cover={
              <div className="flex size-full items-center justify-center p-[10%]">
                <Image
                  src={skin.preview_url ?? skin.texture_url}
                  alt=""
                  width={128}
                  height={skin.preview_url ? 256 : 128}
                  unoptimized
                  className="size-full object-contain [image-rendering:pixelated]"
                />
              </div>
            }
          />
        ))}
      </CardGrid>
    </div>
  );
}
