import type { Metadata } from "next";

import { FormPage } from "@/components/layout/FormPage";
import { authCopy } from "@/features/auth/copy";
import { PasswordResetRequestForm } from "@/features/auth/PasswordResetRequestForm";

const copy = authCopy.reset;

export const metadata: Metadata = { title: copy.title };

export default function PasswordResetPage() {
  return (
    <FormPage title={copy.title} description={copy.description}>
      <PasswordResetRequestForm />
    </FormPage>
  );
}
