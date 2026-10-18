import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { getServer } from "@/features/servers/api";
import { serversCopy } from "@/features/servers/copy";
import { EditServer } from "@/features/servers/EditServer";

export const metadata: Metadata = { title: serversCopy.form.editTitle, robots: { index: false } };

export default function EditServerPage({ params }: PageProps<"/servers/[slug]/edit">) {
  return (
    <FormPage title={serversCopy.form.editTitle}>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <Edit params={params} />
      </Suspense>
    </FormPage>
  );
}

async function Edit({ params }: Pick<PageProps<"/servers/[slug]/edit">, "params">) {
  const server = await getServer((await params).slug);
  // Only the owner edits; others get the same «not found» as for a missing server
  if (!server?.is_mine) notFound();
  return <EditServer server={server} />;
}
