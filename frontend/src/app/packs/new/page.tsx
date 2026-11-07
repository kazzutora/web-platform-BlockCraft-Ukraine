import type { Metadata } from "next";

import { FormPage } from "@/components/layout/FormPage";
import { packsCopy } from "@/features/packs/copy";
import { NewPack } from "@/features/packs/NewPack";

export const metadata: Metadata = { title: packsCopy.form.newTitle, robots: { index: false } };

export default function NewPackPage() {
  return (
    <FormPage title={packsCopy.form.newTitle} description={packsCopy.form.newDescription}>
      <NewPack />
    </FormPage>
  );
}
