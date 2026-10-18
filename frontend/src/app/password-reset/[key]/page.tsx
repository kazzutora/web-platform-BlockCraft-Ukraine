import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { authCopy } from "@/features/auth/copy";
import { decodeKey } from "@/features/auth/decodeKey";
import { PasswordResetForm } from "@/features/auth/PasswordResetForm";

const copy = authCopy.reset;

export const metadata: Metadata = { title: copy.newTitle };

export default function NewPasswordPage({ params }: PageProps<"/password-reset/[key]">) {
  return (
    <FormPage title={copy.newTitle}>
      <Suspense fallback={<Skeleton className="h-48 w-full" />}>
        <ResetFromParams params={params} />
      </Suspense>
    </FormPage>
  );
}

async function ResetFromParams({ params }: Pick<PageProps<"/password-reset/[key]">, "params">) {
  const { key } = await params;
  return <PasswordResetForm resetKey={decodeKey(key)} />;
}
