import type { Metadata } from "next";
import Link from "next/link";

import { Container } from "@/components/layout/Container";
import { Icon } from "@/components/ui/Icon";
import { shareCopy as copy } from "@/features/share/copy";

export const metadata: Metadata = { title: copy.title, description: copy.description };

/** «Поділитися»: every way a player gives something back, one tap each. */
export default function SharePage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <header className="flex max-w-prose flex-col gap-4">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="text-muted">{copy.description}</p>
      </header>
      <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {copy.actions.map((action) => (
          <li key={action.href}>
            <Link
              href={action.href}
              className="flex h-full flex-col gap-3 border border-line p-6 hover:border-text focus-visible:outline-2 focus-visible:outline-accent"
            >
              <Icon name={action.icon} size={24} />
              <span className="font-serif text-h2">{action.title}</span>
              <span className="text-sm text-muted">{action.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Container>
  );
}
