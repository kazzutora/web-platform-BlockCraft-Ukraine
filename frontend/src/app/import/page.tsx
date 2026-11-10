import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { importCopy as copy } from "@/features/import/copy";
import { ImportChecker } from "@/features/import/ImportChecker";

export const metadata: Metadata = { title: copy.title, description: copy.intro };

/** /import: the player's own mods, checked without uploading them (tech.md 10.5). */
export default function ImportPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <div className="flex flex-col gap-4">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="max-w-prose text-lg text-muted">{copy.intro}</p>
      </div>
      <ImportChecker />
    </Container>
  );
}
