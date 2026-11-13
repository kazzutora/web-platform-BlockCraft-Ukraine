import { type CatalogQuery, type PackLoader, packLoaders } from "./types";

export type PackOrigin = "modrinth" | "community";
const origins: PackOrigin[] = ["modrinth", "community"];

/** Catalog state, kept in the URL query string. */
export type PackFilters = {
  gameVersion: string;
  loader: PackLoader | "";
  origin: PackOrigin | "";
  sort: string;
  q: string;
  page: number;
  /** «Усі версії»: ignore the defaults from «Моя гра». */
  all: boolean;
};

type SearchParams = Record<string, string | string[] | undefined>;

const sorts = ["popular", "new", "top", "downloads"];
// Release numbers only ("1.21.1", "26.3"); the API checks they are supported
const RELEASE = /^\d+\.\d+(\.\d+)?$/;

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export function parseFilters(params: SearchParams): PackFilters {
  const gameVersion = first(params.version);
  const loader = first(params.loader) as PackLoader;
  const origin = first(params.origin) as PackOrigin;
  const sort = first(params.sort);
  return {
    gameVersion: RELEASE.test(gameVersion) ? gameVersion : "",
    loader: packLoaders.includes(loader) ? loader : "",
    origin: origins.includes(origin) ? origin : "",
    sort: sorts.includes(sort) ? sort : "",
    q: first(params.q),
    page: Math.max(1, Number.parseInt(first(params.page), 10) || 1),
    all: first(params.all) === "1",
  };
}

type Game = { game_version?: string | null; loader?: string } | null;

/** Version and loader from «Моя гра» unless the URL says otherwise (vanilla has no packs). */
export function withGameDefaults(
  filters: PackFilters,
  game: Game,
): { filters: PackFilters; fromGame: boolean } {
  if (filters.all || !game) return { filters, fromGame: false };
  const next = { ...filters };
  let fromGame = false;
  if (!next.gameVersion && game.game_version) {
    next.gameVersion = game.game_version;
    fromGame = true;
  }
  if (!next.loader && packLoaders.includes(game.loader as PackLoader)) {
    next.loader = game.loader as PackLoader;
    fromGame = true;
  }
  return { filters: next, fromGame };
}

export function toApiQuery(filters: PackFilters, page = filters.page): CatalogQuery {
  // Game parameters always go explicitly: the page shows exactly what it filters by
  const query: CatalogQuery = {
    page,
    game_version: filters.gameVersion,
    loader: filters.loader as CatalogQuery["loader"],
  };
  if (filters.origin) query.origin = filters.origin;
  if (filters.sort) query.sort = filters.sort as CatalogQuery["sort"];
  if (filters.q) query.q = filters.q;
  return query;
}

/** Link to the catalog with some filters changed; changing filters resets the page. */
export function catalogHref(filters: PackFilters, change: Partial<PackFilters> = {}): string {
  const next = { ...filters, page: 1, ...change };
  const params = new URLSearchParams();
  if (next.gameVersion) params.set("version", next.gameVersion);
  if (next.loader) params.set("loader", next.loader);
  if (next.origin) params.set("origin", next.origin);
  if (next.sort) params.set("sort", next.sort);
  if (next.q) params.set("q", next.q);
  if (next.all) params.set("all", "1");
  const query = params.toString();
  return query ? `/packs?${query}` : "/packs";
}

/**
 * Versions next to `target` in the supported list (newest first), closest first and the
 * newer one first on a tie: where to look when «Моя гра» has no ready packs.
 */
export function nearestVersions(target: string, versions: string[], limit = 8): string[] {
  const at = versions.indexOf(target);
  if (at < 0) return [];
  return versions
    .map((version, index) => ({ version, distance: Math.abs(index - at), newer: index < at }))
    .filter((item) => item.version !== target)
    .sort((a, b) => a.distance - b.distance || Number(b.newer) - Number(a.newer))
    .slice(0, limit)
    .map((item) => item.version);
}
