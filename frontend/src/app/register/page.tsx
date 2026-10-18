import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { authCopy } from "@/features/auth/copy";
import { RegisterForm } from "@/features/auth/RegisterForm";

const copy = authCopy.register;

export const metadata: Metadata = { title: copy.title };

export default function RegisterPage() {
  return (
    <FormPage title={copy.title} description={copy.description}>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <RegisterForm />
      </Suspense>
    </FormPage>
  );
}
