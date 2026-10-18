import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { skinsCopy } from "@/features/skins/copy";
import { SkinLookup } from "@/features/skins/SkinLookup";

const copy = skinsCopy.lookupPage;

export const metadata: Metadata = { title: copy.title, description: copy.description };

export default function SkinLookupPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <header className="flex flex-col gap-3">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="text-muted">{copy.description}</p>
      </header>
      <Suspense fallback={<Skeleton className="h-12 w-full max-w-md" />}>
        <SkinLookup />
      </Suspense>
    </Container>
  );
}
