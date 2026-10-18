import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getProject } from "@/features/mods/api";
import { ModDetail } from "@/features/mods/ModDetail";

export async function generateMetadata({ params }: PageProps<"/mods/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const project = await getProject(slug);
  if (!project) return {};
  return { title: project.title, description: project.summary };
}

export default function ModPage({ params, searchParams }: PageProps<"/mods/[slug]">) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <Detail params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function Detail({ params, searchParams }: PageProps<"/mods/[slug]">) {
  const [{ slug }, query] = await Promise.all([params, searchParams]);
  return <ModDetail slug={slug} searchParams={query} />;
}

function DetailSkeleton() {
  return (
    <Container className="grid gap-10 py-12 md:grid-cols-2 md:gap-16 md:py-16">
      <Skeleton className="aspect-square w-full" />
      <div className="flex flex-col justify-center gap-6">
        <Skeleton className="h-7 w-20" />
        <Skeleton className="h-16 w-3/4" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-72" />
      </div>
    </Container>
  );
}
