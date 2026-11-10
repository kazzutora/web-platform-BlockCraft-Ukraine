import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getPack } from "@/features/packs/api";
import { packsCopy } from "@/features/packs/copy";
import { PackBuilder } from "@/features/packs/PackBuilder";

export const metadata: Metadata = { title: packsCopy.builder.chip, robots: { index: false } };

export default function EditPackPage({ params }: PageProps<"/packs/[slug]/edit">) {
  return (
    <Suspense fallback={<BuilderSkeleton />}>
      <Builder params={params} />
    </Suspense>
  );
}

async function Builder({ params }: Pick<PageProps<"/packs/[slug]/edit">, "params">) {
  const pack = await getPack((await params).slug);
  // Only the author builds; others get the same «not found» as for a missing pack
  if (!pack?.is_mine || pack.origin === "modrinth") notFound();
  return <PackBuilder initial={pack} />;
}

function BuilderSkeleton() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <Skeleton className="h-16 w-2/3" />
      <div className="grid gap-10 md:grid-cols-2">
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    </Container>
  );
}
