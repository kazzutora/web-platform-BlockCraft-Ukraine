import { Suspense } from "react";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Illustration } from "@/components/ui/Illustration";
import { Skeleton } from "@/components/ui/Skeleton";
import { GameChipArea } from "@/features/game/GameChipArea";

import { homeCopy as copy } from "./copy";

/** Display title, one line, «Моя гра» and the search field (tech.md 10.4). */
export function Hero() {
  return (
    <section className="flex flex-col items-center gap-8 pt-8 text-center md:pt-16">
      <Illustration name="home" size={160} className="md:size-48" />
      <h1 className="text-display">{copy.title}</h1>
      <p className="max-w-prose text-lg text-muted">{copy.lead}</p>
      {/* On phones the chip already sits right under the header */}
      <div className="hidden md:block">
        <Suspense fallback={<Skeleton className="h-10 w-48" />}>
          <GameChipArea />
        </Suspense>
      </div>
      {/* A plain GET form: Ctrl+K opens the overlay with suggestions */}
      <form
        action="/search"
        role="search"
        className="flex w-full max-w-xl items-stretch border border-text bg-surface"
      >
        <label className="flex min-w-0 flex-1 items-center gap-3 px-4">
          <Icon name="search" className="text-muted" />
          <span className="sr-only">{copy.search}</span>
          <input
            type="search"
            name="q"
            maxLength={100}
            placeholder={copy.search}
            className="h-14 min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
          />
        </label>
        <Button type="submit" size="lg" className="h-auto rounded-none">
          {copy.searchButton}
        </Button>
      </form>
    </section>
  );
}
