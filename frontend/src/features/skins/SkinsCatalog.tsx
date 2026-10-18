import { CatalogPage } from "@/components/layout/CatalogPage";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { plural } from "@/lib/plural";

import { getCatalog } from "./api";
import { skinsCopy } from "./copy";
import { type SkinFilters as Filters, toApiQuery } from "./filters";
import { LoadMoreSkins } from "./LoadMoreSkins";
import { SkinCard } from "./SkinCard";
import { SkinFilters } from "./SkinFilters";

/** /skins: server-rendered first page with colour, model and style filters. */
export async function SkinsCatalog({ filters }: { filters: Filters }) {
  const query = toApiQuery(filters);
  const page = await getCatalog(query);

  return (
    <CatalogPage
      illustration="skins"
      title={skinsCopy.title}
      count={plural(page.count, skinsCopy.plural)}
      filters={
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-3">
            <ButtonLink href="/skins/new">
              <Icon name="upload" />
              {skinsCopy.upload}
            </ButtonLink>
            <ButtonLink href="/skins/lookup" variant="secondary">
              <Icon name="search" />
              {skinsCopy.lookup}
            </ButtonLink>
          </div>
          <SkinFilters filters={filters} />
        </div>
      }
      footer={
        page.next ? (
          <LoadMoreSkins key={JSON.stringify(query)} query={query} startPage={filters.page + 1} />
        ) : null
      }
    >
      {page.results.length ? (
        <CardGrid>
          {page.results.map((skin, index) => (
            <SkinCard key={skin.id} skin={skin} eager={index < 4} />
          ))}
        </CardGrid>
      ) : (
        <EmptyState title={skinsCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
