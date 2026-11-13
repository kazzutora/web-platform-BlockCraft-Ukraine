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
import {
  catalogHref,
  type PackFilters as Filters,
  nearestVersions,
  toApiQuery,
  withGameDefaults,
} from "./filters";
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
      ) : fromGame && filters.gameVersion ? (
        <NothingForGame filters={filters} gameVersions={gameVersions} gameLabel={gameLabel} />
      ) : (
        <EmptyState title={packsCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}

/**
 * Nothing for «Моя гра» (1.21.4 · NeoForge has almost no modpacks): the closest version
 * with ready packs for the same loader — a pack installs its own game version — and an
 * offer to build one for this game.
 */
async function NothingForGame({
  filters,
  gameVersions,
  gameLabel,
}: {
  filters: Filters;
  gameVersions: string[];
  gameLabel: string;
}) {
  const candidates = nearestVersions(filters.gameVersion, gameVersions);
  const pages = await Promise.all(
    candidates.map((gameVersion) => getCatalog(toApiQuery({ ...filters, gameVersion }, 1))),
  );
  const found = pages.findIndex((candidate) => candidate.results.length);
  const nearest = found >= 0 ? { version: candidates[found], page: pages[found] } : null;
  const nearestFilters = nearest ? { ...filters, gameVersion: nearest.version } : null;
  const nearestLabel = nearest
    ? [nearest.version, filters.loader && loaderName(filters.loader)].filter(Boolean).join(" · ")
    : "";

  return (
    <div className="flex flex-col gap-12">
      <EmptyState
        title={packsCopy.noneForGame(gameLabel)}
        illustration="packs"
        action={
          <ButtonLink href="/help/goal" variant="secondary">
            {packsCopy.buildOwn}
          </ButtonLink>
        }
      />
      {nearest && nearestFilters && (
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-2 border-b border-line pb-4">
            <h2 className="text-h2">{packsCopy.nearest(nearestLabel)}</h2>
            <p className="max-w-prose text-sm text-muted">{packsCopy.nearestHint}</p>
          </div>
          <CardGrid>
            {nearest.page.results.slice(0, 8).map((pack) => (
              <PackCard key={pack.slug} pack={pack} />
            ))}
          </CardGrid>
          <ButtonLink
            href={catalogHref(nearestFilters)}
            variant="ghost"
            className="self-start px-0"
          >
            {packsCopy.nearestAll(nearestLabel)}
            <Icon name="chevron-right" size={16} />
          </ButtonLink>
        </section>
      )}
    </div>
  );
}
