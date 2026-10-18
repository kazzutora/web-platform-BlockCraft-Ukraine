import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { libraryCopy } from "@/features/library/copy";
import { MyCollections } from "@/features/library/MyCollections";

export const metadata: Metadata = { title: libraryCopy.mine.title };

export default function MyCollectionsPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{libraryCopy.mine.title}</h1>
      <MyCollections />
    </Container>
  );
}
