import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { type TopKind, TopList, type TopPeriod, topCopy } from "@/features/home/TopList";

export const metadata: Metadata = {
  title: topCopy.title,
  description: "Найпопулярніші моди, скіни й сервери тижня, місяця й усіх часів.",
};

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export default function TopPage({ searchParams }: PageProps<"/top">) {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{topCopy.title}</h1>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <Top searchParams={searchParams} />
      </Suspense>
    </Container>
  );
}

async function Top({ searchParams }: Pick<PageProps<"/top">, "searchParams">) {
  const params = await searchParams;
  const kind = first(params.kind) as TopKind;
  const period = first(params.period) as TopPeriod;
  return (
    <TopList
      kind={Object.hasOwn(topCopy.kinds, kind) ? kind : "mod"}
      period={Object.hasOwn(topCopy.periods, period) ? period : "week"}
    />
  );
}
