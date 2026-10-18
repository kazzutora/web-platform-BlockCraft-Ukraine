import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { libraryCopy } from "@/features/library/copy";
import { SavedTabs } from "@/features/library/SavedTabs";

export const metadata: Metadata = { title: libraryCopy.saved.title };

export default function SavedPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{libraryCopy.saved.title}</h1>
      <SavedTabs />
    </Container>
  );
}
