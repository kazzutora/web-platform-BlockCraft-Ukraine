import { Suspense } from "react";

import { IconLink } from "@/components/ui/IconLink";
import { Skeleton } from "@/components/ui/Skeleton";
import { AccountArea } from "@/features/auth/AccountArea";

import { Container } from "./Container";
import { Logo } from "./Logo";
import { MobileMenu } from "./MobileMenu";
import { SectionLinks } from "./SectionLinks";
import { SectionNav } from "./SectionNav";
import { ThemeToggle } from "./ThemeToggle";

const copy = { search: "Пошук", saved: "Обране" };

/** Sections on the left, logo in the center, search / saved / account on the right. */
export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg">
      <Container className="flex h-16 items-center justify-between md:grid md:grid-cols-[1fr_auto_1fr]">
        <div className="hidden md:block">
          <Suspense fallback={<SectionLinks />}>
            <SectionNav />
          </Suspense>
        </div>
        <Logo />
        <div className="flex items-center justify-end gap-1">
          <IconLink href="/search" icon="search" label={copy.search} />
          {/* Desktop-only actions; on phones they live in the menu and the tab bar */}
          <div className="hidden items-center gap-1 md:flex">
            <IconLink href="/me/saved" icon="bookmark" label={copy.saved} />
            <ThemeToggle />
            <Suspense fallback={<Skeleton className="size-8" />}>
              <AccountArea />
            </Suspense>
          </div>
          <div className="md:hidden">
            <MobileMenu />
          </div>
        </div>
      </Container>
    </header>
  );
}
