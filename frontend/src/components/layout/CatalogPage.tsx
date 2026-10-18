import type { ReactNode } from "react";

import { Illustration, type IllustrationName } from "@/components/ui/Illustration";

import { Container } from "./Container";

type CatalogPageProps = {
  illustration: IllustrationName;
  title: string;
  /** Already formatted, e.g. `plural(312, …)` → «312 модів». */
  count?: string;
  /** Row of FilterChips. */
  filters?: ReactNode;
  /** Usually a CardGrid, EmptyState or skeletons. */
  children: ReactNode;
  /** «Показати ще». */
  footer?: ReactNode;
};

/** Catalog template: illustration, H1 with a counter, filters, grid, «show more». */
export function CatalogPage({
  illustration,
  title,
  count,
  filters,
  children,
  footer,
}: CatalogPageProps) {
  return (
    <Container className="flex flex-col gap-10 py-12 md:gap-16 md:py-16">
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:gap-10">
        <Illustration name={illustration} size={128} className="md:size-40" />
        <div className="flex flex-col gap-2">
          <h1 className="text-h1">{title}</h1>
          {count && <p className="text-muted tabular-nums">{count}</p>}
        </div>
      </header>
      {filters}
      <section>{children}</section>
      {footer}
    </Container>
  );
}
