import type { Metadata } from "next";
import { Suspense } from "react";

import { skinsCopy } from "@/features/skins/copy";
import { parseFilters } from "@/features/skins/filters";
import { SkinsCatalog } from "@/features/skins/SkinsCatalog";

import Loading from "../loading";

export const metadata: Metadata = {
  title: skinsCopy.title,
  description: "Скіни Minecraft від гравців: фільтри за кольором і стилем, 3D-перегляд.",
};

export default function SkinsPage({ searchParams }: PageProps<"/skins">) {
  return (
    <Suspense fallback={<Loading />}>
      <Catalog searchParams={searchParams} />
    </Suspense>
  );
}

async function Catalog({ searchParams }: Pick<PageProps<"/skins">, "searchParams">) {
  return <SkinsCatalog filters={parseFilters(await searchParams)} />;
}
