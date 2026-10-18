import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getServer } from "@/features/servers/api";
import { serversCopy } from "@/features/servers/copy";
import { ServerDetail } from "@/features/servers/ServerDetail";

export async function generateMetadata({
  params,
}: PageProps<"/servers/[slug]">): Promise<Metadata> {
  const server = await getServer((await params).slug);
  if (!server) return {};
  return {
    title: `${server.name} — ${serversCopy.label.toLowerCase()} Minecraft`,
    description:
      server.description || `${server.address} · ${serversCopy.editions[server.edition]}`,
    ...(server.status === "published" ? {} : { robots: { index: false } }),
  };
}

export default function ServerPage({ params }: PageProps<"/servers/[slug]">) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: Pick<PageProps<"/servers/[slug]">, "params">) {
  return <ServerDetail slug={(await params).slug} />;
}

function DetailSkeleton() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <Skeleton className="aspect-[4/1] w-full" />
      <Skeleton className="h-16 w-2/3" />
      <Skeleton className="h-12 w-80" />
    </Container>
  );
}
