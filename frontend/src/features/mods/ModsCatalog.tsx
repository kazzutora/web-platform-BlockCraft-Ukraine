import { CatalogPage } from "@/components/layout/CatalogPage";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { plural } from "@/lib/plural";

import { getGameContext } from "@/features/game/context";
import { getGameVersions } from "@/features/game/meta";
import { loaderName } from "./format";
import { ImportFromModrinth } from "./ImportFromModrinth";

import { getCatalog, getCategories } from "./api";
import { CatalogFilters } from "./CatalogFilters";
import { modsCopy } from "./copy";
import { type ModFilters, toApiQuery, withProfileDefaults } from "./filters";
import { LoadMoreMods } from "./LoadMoreMods";
import { ModCard } from "./ModCard";

const illustrations = {
  mod: "mods",
  resourcepack: "packs",
  shader: "worlds",
  datapack: "worlds",
} as const;

/** /mods: server-rendered first page; the version and loader default to «Моя гра». */
export async function ModsCatalog({ filters: requested }: { filters: ModFilters }) {
  const game = await getGameContext();
  const { filters, fromProfile } = withProfileDefaults(requested, game);
  const [page, categories, gameVersions] = await Promise.all([
    getCatalog(toApiQuery(filters)),
    getCategories(filters.type),
    getGameVersions(),
  ]);
  const typeCopy = modsCopy.types[filters.type];
  const gameLabel = [game.game_version, game.loader && loaderName(game.loader)]
    .filter(Boolean)
    .join(" · ");

  return (
    <CatalogPage
      illustration={illustrations[filters.type]}
      title={typeCopy.title}
      count={plural(page.count, typeCopy.plural)}
      filters={
        <CatalogFilters
          filters={filters}
          categories={categories}
          gameVersions={gameVersions}
          fromProfile={fromProfile}
          inviteToChoose={game.source === "none" && !filters.all}
        />
      }
      footer={
        <div className="flex flex-col gap-12">
          {page.next ? (
            <LoadMoreMods
              key={JSON.stringify(toApiQuery(filters))}
              query={toApiQuery(filters)}
              startPage={filters.page + 1}
              gameLabel={gameLabel}
            />
          ) : null}
          <ImportFromModrinth />
        </div>
      }
    >
      {page.results.length ? (
        <CardGrid>
          {page.results.map((project, index) => (
            <ModCard key={project.slug} project={project} eager={index < 4} gameLabel={gameLabel} />
          ))}
        </CardGrid>
      ) : (
        <EmptyState title={modsCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
