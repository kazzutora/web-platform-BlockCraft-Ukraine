import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { authCopy } from "@/features/auth/copy";
import { LoginForm } from "@/features/auth/LoginForm";

const copy = authCopy.login;

export const metadata: Metadata = { title: copy.title };

export default function LoginPage() {
  return (
    <FormPage title={copy.title} description={copy.description}>
      <Suspense fallback={<Skeleton className="h-80 w-full" />}>
        <LoginForm />
      </Suspense>
    </FormPage>
  );
}
