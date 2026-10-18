import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { authCopy } from "@/features/auth/copy";
import { decodeKey } from "@/features/auth/decodeKey";
import { VerifyEmail } from "@/features/auth/VerifyEmail";

const copy = authCopy.verify;

export const metadata: Metadata = { title: copy.title };

export default function VerifyEmailPage({ params }: PageProps<"/verify-email/[key]">) {
  return (
    <FormPage title={copy.title}>
      <Suspense fallback={<Skeleton className="h-24 w-full" />}>
        <VerifyFromParams params={params} />
      </Suspense>
    </FormPage>
  );
}

async function VerifyFromParams({ params }: Pick<PageProps<"/verify-email/[key]">, "params">) {
  const { key } = await params;
  return <VerifyEmail emailKey={decodeKey(key)} />;
}
