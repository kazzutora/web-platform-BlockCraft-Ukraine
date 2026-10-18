import { ButtonLink } from "@/components/ui/ButtonLink";
import { IconLink } from "@/components/ui/IconLink";

import { Container } from "./Container";
import { Logo } from "./Logo";
import { MobileMenu } from "./MobileMenu";
import { SectionNav } from "./SectionNav";
import { ThemeToggle } from "./ThemeToggle";

const copy = { search: "Пошук", saved: "Обране", login: "Увійти" };

/** Sections on the left, logo in the center, search / saved / account on the right. */
export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg">
      <Container className="flex h-16 items-center justify-between md:grid md:grid-cols-[1fr_auto_1fr]">
        <div className="hidden md:block">
          <SectionNav />
        </div>
        <Logo />
        <div className="flex items-center justify-end gap-1">
          <IconLink href="/search" icon="search" label={copy.search} />
          {/* Desktop-only actions; on phones they live in the menu and the tab bar */}
          <div className="hidden items-center gap-1 md:flex">
            <IconLink href="/me/saved" icon="bookmark" label={copy.saved} />
            <ThemeToggle />
            <ButtonLink href="/login" variant="ghost">
              {copy.login}
            </ButtonLink>
          </div>
          <div className="md:hidden">
            <MobileMenu />
          </div>
        </div>
      </Container>
    </header>
  );
}
