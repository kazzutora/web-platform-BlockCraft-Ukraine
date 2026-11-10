import { CatalogPage } from "@/components/layout/CatalogPage";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { plural } from "@/lib/plural";

import { getGameContext } from "@/features/game/context";
import { getGameVersions } from "@/features/game/meta";
import { loaderName } from "@/features/mods/format";

import { getCatalog } from "./api";
import { packsCopy } from "./copy";
import { type PackFilters as Filters, toApiQuery, withGameDefaults } from "./filters";
import { LoadMorePacks } from "./LoadMorePacks";
import { PackCard } from "./PackCard";
import { PackFilters } from "./PackFilters";

/** /packs: server-rendered first page; version and loader default to «Моя гра». */
export async function PacksCatalog({ filters: requested }: { filters: Filters }) {
  const game = await getGameContext();
  const { filters, fromGame } = withGameDefaults(requested, game);
  const query = toApiQuery(filters);
  const [page, gameVersions] = await Promise.all([getCatalog(query), getGameVersions()]);
  const gameLabel = [game.game_version, game.loader && loaderName(game.loader)]
    .filter(Boolean)
    .join(" · ");

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
          <PackFilters
            filters={filters}
            gameVersions={gameVersions}
            fromGame={fromGame}
            inviteToChoose={game.source === "none" && !filters.all}
          />
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
            <PackCard key={pack.slug} pack={pack} eager={index < 4} gameLabel={gameLabel} />
          ))}
        </CardGrid>
      ) : (
        <EmptyState title={packsCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
