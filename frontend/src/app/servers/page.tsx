import type { Metadata } from "next";
import { Suspense } from "react";

import { serversCopy } from "@/features/servers/copy";
import { parseFilters } from "@/features/servers/filters";
import { ServersCatalog } from "@/features/servers/ServersCatalog";

import Loading from "../loading";

export const metadata: Metadata = {
  title: serversCopy.title,
  description: "Українські сервери Minecraft з живим онлайном, режимами й відгуками гравців.",
};

export default function ServersPage({ searchParams }: PageProps<"/servers">) {
  return (
    <Suspense fallback={<Loading />}>
      <Catalog searchParams={searchParams} />
    </Suspense>
  );
}

async function Catalog({ searchParams }: Pick<PageProps<"/servers">, "searchParams">) {
  return <ServersCatalog filters={parseFilters(await searchParams)} />;
}
