import type { ReactNode } from "react";

import { Container } from "@/components/layout/Container";

export type LegalSection = { title: string; body: ReactNode };

type LegalPageProps = {
  title: string;
  lead: string;
  updated: string;
  sections: LegalSection[];
};

/** Text page for the rules and the privacy policy: numbered sections, readable width. */
export function LegalPage({ title, lead, updated, sections }: LegalPageProps) {
  return (
    <Container className="py-12 md:py-16">
      <article className="mx-auto flex max-w-prose flex-col gap-10">
        <header className="flex flex-col gap-4">
          <h1 className="text-h1">{title}</h1>
          <p className="text-lg text-muted">{lead}</p>
          <p className="text-meta text-muted">{updated}</p>
        </header>
        <ol className="flex flex-col gap-10">
          {sections.map((section, index) => (
            <li key={section.title} className="flex flex-col gap-3">
              <h2 className="text-h2">
                <span className="text-muted tabular-nums">{index + 1}. </span>
                {section.title}
              </h2>
              <div className="flex flex-col gap-3 leading-relaxed">{section.body}</div>
            </li>
          ))}
        </ol>
      </article>
    </Container>
  );
}
