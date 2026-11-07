import type { Metadata } from "next";
import { Suspense } from "react";

import { packsCopy } from "@/features/packs/copy";
import { parseFilters } from "@/features/packs/filters";
import { PacksCatalog } from "@/features/packs/PacksCatalog";

import Loading from "../loading";

export const metadata: Metadata = {
  title: packsCopy.title,
  description: "Зборки модів Minecraft від гравців: один файл .mrpack — і все встановлено.",
};

export default function PacksPage({ searchParams }: PageProps<"/packs">) {
  return (
    <Suspense fallback={<Loading />}>
      <Catalog searchParams={searchParams} />
    </Suspense>
  );
}

async function Catalog({ searchParams }: Pick<PageProps<"/packs">, "searchParams">) {
  return <PacksCatalog filters={parseFilters(await searchParams)} />;
}
