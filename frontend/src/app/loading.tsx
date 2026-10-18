import { Container } from "@/components/layout/Container";
import { CardGrid } from "@/components/ui/CardGrid";
import { Skeleton } from "@/components/ui/Skeleton";

const copy = { loading: "Завантажуємо…" };

export default function Loading() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <p role="status" className="sr-only">
        {copy.loading}
      </p>
      <Skeleton className="h-16 w-2/3 max-w-md" />
      <CardGrid>
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="flex flex-col gap-3">
            <Skeleton className="aspect-square w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </CardGrid>
    </Container>
  );
}
