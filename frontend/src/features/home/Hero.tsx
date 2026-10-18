import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Illustration } from "@/components/ui/Illustration";

import { homeCopy as copy } from "./copy";

/** Display title, one line, the search field and the island illustration. */
export function Hero() {
  return (
    <section className="flex flex-col items-center gap-8 pt-8 text-center md:pt-16">
      <Illustration name="home" size={160} className="md:size-48" />
      <h1 className="text-display">{copy.title}</h1>
      <p className="max-w-prose text-lg text-muted">{copy.lead}</p>
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
