import type { Metadata } from "next";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { searchCopy as copy } from "@/features/search/copy";
import { SearchResults } from "@/features/search/SearchResults";
import { type SearchKind, searchKinds } from "@/features/search/types";

export const metadata: Metadata = { title: copy.title, robots: { index: false } };

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export default function SearchPage({ searchParams }: PageProps<"/search">) {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{copy.title}</h1>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <Results searchParams={searchParams} />
      </Suspense>
    </Container>
  );
}

async function Results({ searchParams }: Pick<PageProps<"/search">, "searchParams">) {
  const params = await searchParams;
  const q = first(params.q).slice(0, 100);
  const kind = first(params.kind) as SearchKind;
  const page = Math.max(1, Number.parseInt(first(params.page), 10) || 1);

  return (
    <div className="flex flex-col gap-10">
      {/* A plain GET form: works before the page hydrates and without the overlay */}
      <form action="/search" className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <div className="sm:w-[32rem]">
          <Input
            type="search"
            name="q"
            label={copy.label}
            hideLabel
            placeholder={copy.placeholder}
            defaultValue={q}
            maxLength={100}
          />
        </div>
        {searchKinds.includes(kind) && <input type="hidden" name="kind" value={kind} />}
        <Button type="submit" size="lg">
          {copy.submit}
        </Button>
      </form>
      {q ? (
        <SearchResults q={q} kind={searchKinds.includes(kind) ? kind : undefined} page={page} />
      ) : (
        <p className="text-muted">{copy.hint}</p>
      )}
    </div>
  );
}
