import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { skinsCopy } from "@/features/skins/copy";
import { SkinUploadForm } from "@/features/skins/SkinUploadForm";

export const metadata: Metadata = { title: skinsCopy.form.title, robots: { index: false } };

export default function NewSkinPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{skinsCopy.form.title}</h1>
      <SkinUploadForm />
    </Container>
  );
}
