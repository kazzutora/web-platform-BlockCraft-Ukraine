import type { Metadata } from "next";

import { FormPage } from "@/components/layout/FormPage";
import { serversCopy } from "@/features/servers/copy";
import { NewServer } from "@/features/servers/NewServer";

export const metadata: Metadata = { title: serversCopy.form.newTitle, robots: { index: false } };

export default function NewServerPage() {
  return (
    <FormPage title={serversCopy.form.newTitle}>
      <NewServer />
    </FormPage>
  );
}
