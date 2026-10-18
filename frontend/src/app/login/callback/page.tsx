import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { authCopy } from "@/features/auth/copy";
import { ProviderCallback } from "@/features/auth/ProviderCallback";

export const metadata: Metadata = { title: authCopy.login.title };

export default function ProviderCallbackPage() {
  return (
    <FormPage title={authCopy.login.title}>
      <Suspense fallback={<Skeleton className="h-24 w-full" />}>
        <ProviderCallback />
      </Suspense>
    </FormPage>
  );
}
