import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { CardGrid } from "@/components/ui/CardGrid";
import { Skeleton } from "@/components/ui/Skeleton";
import { Hero } from "@/features/home/Hero";
import { HomeSections } from "@/features/home/HomeSections";

export default function HomePage() {
  return (
    <Container className="flex flex-col gap-28 py-12 md:gap-36 md:py-16">
      <Hero />
      <Suspense fallback={<SectionsSkeleton />}>
        <HomeSections />
      </Suspense>
    </Container>
  );
}

function SectionsSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      <Skeleton className="h-6 w-64" />
      <CardGrid>
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="aspect-square w-full" />
        ))}
      </CardGrid>
    </div>
  );
}
