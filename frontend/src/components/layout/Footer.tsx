import Link from "next/link";

import { sourcesCopy } from "@/features/sources/copy";

import { Container } from "./Container";
import { Logo } from "./Logo";

const copy = {
  tagline: "Моди, скіни й сервери Minecraft українською.",
  disclaimer: "Не є офіційним продуктом Minecraft. Не пов’язано з Mojang або Microsoft.",
  links: [
    { href: "/sources", label: sourcesCopy.title },
    { href: "/rules", label: "Правила" },
    { href: "/privacy", label: "Приватність" },
  ],
  linksLabel: "Інформація",
};

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line pt-12 pb-28 md:pb-12">
      <Container className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
        <div className="flex flex-col gap-3">
          <Logo />
          <p className="text-muted">{copy.tagline}</p>
        </div>
        <nav aria-label={copy.linksLabel}>
          <ul className="flex flex-wrap gap-x-6 gap-y-2">
            {copy.links.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="caps text-muted hover:text-text">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </Container>
      <Container className="mt-8 flex flex-col gap-1">
        <p className="text-meta text-muted">
          <Link href="/sources" className="underline-offset-4 hover:text-text hover:underline">
            {sourcesCopy.footer}
          </Link>
        </p>
        <p className="text-meta text-muted">{copy.disclaimer}</p>
      </Container>
    </footer>
  );
}
