"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { skinsCopy } from "@/features/skins/copy";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";
import { ServerRow } from "./ServerRow";

/** /me/works → «Сервери»: my servers with their moderation status. */
export function MyServers() {
  const servers = useQuery({
    queryKey: queryKeys.servers.mine(),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/servers", {
        params: { query: { page_size: 60 } },
      });
      if (!data) throw new Error("GET /api/v1/me/servers failed");
      return data;
    },
  });

  const add = (
    <ButtonLink href="/servers/new">
      <Icon name="plus" />
      {serversCopy.add}
    </ButtonLink>
  );

  if (servers.isPending) return <Skeleton className="h-40 w-full" />;
  if (servers.isError) return <EmptyState illustration="error" title={serversCopy.detail.error} />;
  if (!servers.data.results.length) {
    return <EmptyState illustration="servers" title={serversCopy.mine.empty} action={add} />;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>{add}</div>
      <ul className="flex flex-col border-t border-line">
        {servers.data.results.map((server) => (
          <ServerRow
            key={server.slug}
            server={server}
            badge={
              server.status !== "published" && (
                <Badge tone="accent">{skinsCopy.mine.status[server.status]}</Badge>
              )
            }
          />
        ))}
      </ul>
    </div>
  );
}
