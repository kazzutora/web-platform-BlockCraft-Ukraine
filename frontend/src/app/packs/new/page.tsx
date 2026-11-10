import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/Skeleton";

import { FormPage } from "@/components/layout/FormPage";
import { packsCopy } from "@/features/packs/copy";
import { NewPack } from "@/features/packs/NewPack";

export const metadata: Metadata = { title: packsCopy.form.newTitle, robots: { index: false } };

export default function NewPackPage() {
  return (
    <FormPage title={packsCopy.form.newTitle} description={packsCopy.form.newDescription}>
      {/* Reads ?items= from the URL */}
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <NewPack />
      </Suspense>
    </FormPage>
  );
}
