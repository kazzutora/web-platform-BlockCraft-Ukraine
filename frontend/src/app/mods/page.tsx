import type { Metadata } from "next";
import { Suspense } from "react";

import { modsCopy } from "@/features/mods/copy";
import { parseFilters } from "@/features/mods/filters";
import { ModsCatalog } from "@/features/mods/ModsCatalog";

import Loading from "../loading";

export const metadata: Metadata = {
  title: modsCopy.types.mod.title,
  description: "Моди, ресурспаки й шейдери з Modrinth — під твою версію Minecraft.",
};

export default function ModsPage({ searchParams }: PageProps<"/mods">) {
  return (
    <Suspense fallback={<Loading />}>
      <Catalog searchParams={searchParams} />
    </Suspense>
  );
}

async function Catalog({ searchParams }: Pick<PageProps<"/mods">, "searchParams">) {
  return <ModsCatalog filters={parseFilters(await searchParams)} />;
}
