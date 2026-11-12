import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { helpCopy } from "@/features/help/copy";
import { CrashChecker } from "@/features/help/CrashChecker";

const copy = helpCopy.crash;

export const metadata: Metadata = { title: copy.title, description: copy.description };

/** /help/crash: the log is read in the browser; only mod ids reach the server. */
export default function CrashPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <header className="flex max-w-prose flex-col gap-4">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="text-lg text-muted">{copy.description}</p>
      </header>
      <CrashChecker />
    </Container>
  );
}
