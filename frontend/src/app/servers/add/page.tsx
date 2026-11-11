import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { AddServer } from "@/features/servers/AddServer";
import { serversCopy } from "@/features/servers/copy";

export const metadata: Metadata = { title: serversCopy.addForm.title, robots: { index: false } };

export default function AddServerPage() {
  return (
    <FormPage title={serversCopy.addForm.title} description={serversCopy.addForm.lead}>
      {/* Reads ?address= from the URL */}
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <AddServer />
      </Suspense>
    </FormPage>
  );
}
