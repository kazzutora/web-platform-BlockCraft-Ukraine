import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Illustration } from "@/components/ui/Illustration";
import { Skeleton } from "@/components/ui/Skeleton";
import { HealthStatus } from "@/features/health/HealthStatus";

const copy = {
  title: "BlockCraft Ukraine",
  lead: "Моди, скіни й сервери Minecraft українською. Головна сторінка з’явиться на етапі 7.",
};

export default function HomePage() {
  return (
    <Container className="flex flex-1 flex-col items-center justify-center gap-10 py-24 text-center">
      <Illustration name="home" size={160} />
      <h1 className="text-display">{copy.title}</h1>
      <p className="max-w-prose text-muted">{copy.lead}</p>
      <Suspense fallback={<Skeleton className="h-24 w-64" />}>
        <HealthStatus />
      </Suspense>
    </Container>
  );
}
