import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { sourcesCopy as copy } from "@/features/sources/copy";
import { SourcesList } from "@/features/sources/SourcesList";

export const metadata: Metadata = {
  title: copy.title,
  description: copy.description,
};

export default function SourcesPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <div className="flex flex-col gap-4">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="max-w-prose text-lg text-muted">{copy.lead}</p>
      </div>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <SourcesList />
      </Suspense>
      <p className="text-meta text-muted">{copy.disclaimer}</p>
    </Container>
  );
}
