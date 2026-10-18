import type { Metadata } from "next";
import Link from "next/link";

import { Container } from "@/components/layout/Container";
import { Illustration, type IllustrationName } from "@/components/ui/Illustration";

const copy = {
  title: "Що додаємо?",
  options: [
    {
      href: "/skins/new",
      art: "skins",
      title: "Скін",
      text: "PNG 64×64: перевіримо, покажемо в 3D і додамо в каталог.",
    },
    {
      href: "/servers/new",
      art: "servers",
      title: "Сервер",
      text: "Адреса й режими: онлайн з’явиться за кілька хвилин.",
    },
  ] satisfies Array<{ href: string; art: IllustrationName; title: string; text: string }>,
};

export const metadata: Metadata = { title: copy.title, robots: { index: false } };

/** /create (the «Додати» tab): pick what to share. */
export default function CreatePage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{copy.title}</h1>
      <ul className="grid gap-6 sm:grid-cols-2">
        {copy.options.map((option) => (
          <li key={option.href}>
            <Link
              href={option.href}
              className="flex h-full flex-col gap-4 border border-line p-6 hover:border-text"
            >
              <Illustration name={option.art} size={96} />
              <span className="text-h2">{option.title}</span>
              <span className="text-muted">{option.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Container>
  );
}
