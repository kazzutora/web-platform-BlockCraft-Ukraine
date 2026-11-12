import type { Metadata } from "next";
import Link from "next/link";

import { Container } from "@/components/layout/Container";
import { Icon } from "@/components/ui/Icon";
import { helpCopy } from "@/features/help/copy";

const copy = helpCopy.hub;

export const metadata: Metadata = { title: copy.title, description: copy.description };

/** «Що не так з грою?»: a player starts from the problem, the site leads to the tool. */
export default function HelpPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <header className="flex max-w-prose flex-col gap-4">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="text-lg text-muted">{copy.description}</p>
      </header>
      <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {copy.problems.map((problem) => (
          <li key={problem.href}>
            <Link
              href={problem.href}
              className="flex h-full flex-col gap-3 border border-line p-6 hover:border-text focus-visible:outline-2 focus-visible:outline-accent"
            >
              <Icon name={problem.icon} size={24} />
              <span className="font-display text-h2">{problem.title}</span>
              <span className="text-sm text-muted">{problem.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Container>
  );
}
