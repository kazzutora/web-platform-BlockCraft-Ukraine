import { CatalogPage } from "@/components/layout/CatalogPage";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { plural } from "@/lib/plural";

import { getCatalog, getCategories, getGameProfile } from "./api";
import { CatalogFilters } from "./CatalogFilters";
import { modsCopy } from "./copy";
import { type ModFilters, toApiQuery, withProfileDefaults } from "./filters";
import { LoadMoreMods } from "./LoadMoreMods";
import { ModCard } from "./ModCard";

/** /mods: server-rendered first page; the version and loader default to the game profile. */
export async function ModsCatalog({ filters: requested }: { filters: ModFilters }) {
  const profile = await getGameProfile();
  const { filters, fromProfile } = withProfileDefaults(requested, profile);
  const [page, categories] = await Promise.all([
    getCatalog(toApiQuery(filters)),
    getCategories(filters.type),
  ]);
  const typeCopy = modsCopy.types[filters.type];

  return (
    <CatalogPage
      illustration={
        filters.type === "shader" ? "worlds" : filters.type === "resourcepack" ? "packs" : "mods"
      }
      title={typeCopy.title}
      count={plural(page.count, typeCopy.plural)}
      filters={
        <CatalogFilters filters={filters} categories={categories} fromProfile={fromProfile} />
      }
      footer={
        page.next ? (
          <LoadMoreMods
            key={JSON.stringify(toApiQuery(filters))}
            query={toApiQuery(filters)}
            startPage={filters.page + 1}
          />
        ) : null
      }
    >
      {page.results.length ? (
        <CardGrid>
          {page.results.map((project, index) => (
            <ModCard key={project.slug} project={project} eager={index < 4} />
          ))}
        </CardGrid>
      ) : (
        <EmptyState title={modsCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
