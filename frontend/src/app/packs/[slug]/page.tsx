import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getPack } from "@/features/packs/api";
import { packsCopy } from "@/features/packs/copy";
import { PackDetail } from "@/features/packs/PackDetail";

export async function generateMetadata({ params }: PageProps<"/packs/[slug]">): Promise<Metadata> {
  const pack = await getPack((await params).slug);
  if (!pack) return {};
  return {
    title: `${pack.title} — ${packsCopy.label.toLowerCase()} Minecraft`,
    description:
      pack.summary || `${pack.game_version} · ${packsCopy.loaders[pack.loader]} · .mrpack`,
    ...(pack.status === "published" ? {} : { robots: { index: false } }),
  };
}

export default function PackPage({ params }: PageProps<"/packs/[slug]">) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: Pick<PageProps<"/packs/[slug]">, "params">) {
  return <PackDetail slug={(await params).slug} />;
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
