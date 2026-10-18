import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getSkin } from "@/features/skins/api";
import { skinsCopy } from "@/features/skins/copy";
import { SkinDetail } from "@/features/skins/SkinDetail";

function parseId(value: string): number {
  return /^\d+$/.test(value) ? Number(value) : 0;
}

export async function generateMetadata({ params }: PageProps<"/skins/[id]">): Promise<Metadata> {
  const id = parseId((await params).id);
  const skin = id ? await getSkin(id) : null;
  if (!skin) return {};
  return {
    title: `${skin.title} — ${skinsCopy.label.toLowerCase()}`,
    description: `${skinsCopy.label} від ${skin.author.nickname}: 3D-перегляд і PNG.`,
    ...(skin.status === "published" ? {} : { robots: { index: false } }),
  };
}

export default function SkinPage({ params }: PageProps<"/skins/[id]">) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: Pick<PageProps<"/skins/[id]">, "params">) {
  return <SkinDetail id={parseId((await params).id)} />;
}

function DetailSkeleton() {
  return (
    <Container className="grid gap-10 py-12 md:grid-cols-2 md:gap-16 md:py-16">
      <Skeleton className="aspect-square w-full" />
      <div className="flex flex-col justify-center gap-6">
        <Skeleton className="h-7 w-20" />
        <Skeleton className="h-16 w-3/4" />
        <Skeleton className="h-12 w-72" />
      </div>
    </Container>
  );
}
