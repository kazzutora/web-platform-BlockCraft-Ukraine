import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getPack } from "@/features/packs/api";
import { packsCopy } from "@/features/packs/copy";
import { PackDetail } from "@/features/packs/PackDetail";

const tokenOf = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value) ?? "";

export async function generateMetadata({
  params,
  searchParams,
}: PageProps<"/packs/[slug]">): Promise<Metadata> {
  const [{ slug }, query] = await Promise.all([params, searchParams]);
  const pack = await getPack(slug, tokenOf(query.share_token));
  if (!pack) return {};
  const listed = pack.status === "published" && pack.visibility === "public";
  return {
    title: `${pack.title} — ${packsCopy.label.toLowerCase()} Minecraft`,
    description:
      pack.summary || `${pack.game_version} · ${packsCopy.loaders[pack.loader]} · .mrpack`,
    ...(listed ? {} : { robots: { index: false } }),
  };
}

export default function PackPage({ params, searchParams }: PageProps<"/packs/[slug]">) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <Detail params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function Detail({ params, searchParams }: PageProps<"/packs/[slug]">) {
  const [{ slug }, query] = await Promise.all([params, searchParams]);
  return <PackDetail slug={slug} shareToken={tokenOf(query.share_token)} />;
}

function DetailSkeleton() {
  return (
    <Container className="grid gap-10 py-12 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] md:py-16">
      <Skeleton className="aspect-square w-full max-w-md" />
      <div className="flex flex-col gap-6">
        <Skeleton className="h-16 w-2/3" />
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-12 w-64" />
      </div>
    </Container>
  );
}
