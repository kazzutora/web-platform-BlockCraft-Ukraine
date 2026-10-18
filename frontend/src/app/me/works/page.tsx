import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { skinsCopy } from "@/features/skins/copy";
import { MySkins } from "@/features/skins/MySkins";

export const metadata: Metadata = { title: skinsCopy.mine.title };

export default function MyWorksPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{skinsCopy.mine.title}</h1>
      <MySkins />
    </Container>
  );
}
