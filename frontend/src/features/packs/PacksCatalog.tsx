import { CatalogPage } from "@/components/layout/CatalogPage";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { plural } from "@/lib/plural";

import { getCatalog } from "./api";
import { packsCopy } from "./copy";
import { type PackFilters as Filters, toApiQuery } from "./filters";
import { LoadMorePacks } from "./LoadMorePacks";
import { PackCard } from "./PackCard";
import { PackFilters } from "./PackFilters";

/** /packs: server-rendered first page of published packs. */
export async function PacksCatalog({ filters }: { filters: Filters }) {
  const query = toApiQuery(filters);
  const page = await getCatalog(query);

  return (
    <CatalogPage
      illustration="packs"
      title={packsCopy.title}
      count={plural(page.count, packsCopy.plural)}
      filters={
        <div className="flex flex-col gap-6">
          <ButtonLink href="/packs/new" className="self-start">
            <Icon name="plus" />
            {packsCopy.create}
          </ButtonLink>
          <PackFilters filters={filters} />
        </div>
      }
      footer={
        page.next ? (
          <LoadMorePacks key={JSON.stringify(query)} query={query} startPage={filters.page + 1} />
        ) : null
      }
    >
      {page.results.length ? (
        <CardGrid>
          {page.results.map((pack, index) => (
            <PackCard key={pack.slug} pack={pack} eager={index < 4} />
          ))}
        </CardGrid>
      ) : (
        <EmptyState title={packsCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
