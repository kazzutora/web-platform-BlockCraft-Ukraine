import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import Loading from "@/app/loading";
import { getCollection } from "@/features/library/api";
import { CollectionView } from "@/features/library/CollectionView";

const pick = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value) ?? "";

export async function generateMetadata({
  params,
  searchParams,
}: PageProps<"/c/[id]">): Promise<Metadata> {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const collection = Number(id) ? await getCollection(Number(id), pick(query.token)) : null;
  return collection
    ? {
        title: collection.title,
        description: collection.description || undefined,
        robots: collection.visibility === "public" ? undefined : { index: false },
      }
    : {};
}

export default function CollectionPage(props: PageProps<"/c/[id]">) {
  return (
    <Suspense fallback={<Loading />}>
      <Collection {...props} />
    </Suspense>
  );
}

async function Collection({ params, searchParams }: PageProps<"/c/[id]">) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const token = pick(query.token);
  const collection = Number(id) ? await getCollection(Number(id), token) : null;
  if (!collection) notFound();
  return <CollectionView initial={collection} shareToken={token} />;
}
