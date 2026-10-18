import { type CatalogQuery, type ProjectType, projectTypes } from "./types";

/** Catalog state, kept in the URL query string. */
export type ModFilters = {
  type: ProjectType;
  game_version: string;
  loader: string;
  categories: string[];
  gpu_load: string;
  sort: string;
  q: string;
  page: number;
  /** «Показати все»: ignore the defaults from the game profile. */
  all: boolean;
};

type SearchParams = Record<string, string | string[] | undefined>;

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export function parseFilters(params: SearchParams): ModFilters {
  const type = first(params.type) as ProjectType;
  return {
    type: projectTypes.includes(type) ? type : "mod",
    game_version: first(params.game_version),
    loader: first(params.loader),
    categories: first(params.category).split(",").filter(Boolean),
    gpu_load: first(params.gpu_load),
    sort: first(params.sort),
    q: first(params.q),
    page: Math.max(1, Number.parseInt(first(params.page), 10) || 1),
    all: first(params.all) === "1",
  };
}

type Profile = { game_version?: string; loader?: string } | null;

/** Fills version and loader from the player's profile unless the URL says otherwise. */
export function withProfileDefaults(
  filters: ModFilters,
  profile: Profile,
): { filters: ModFilters; fromProfile: boolean } {
  if (filters.all || !profile) return { filters, fromProfile: false };
  const next = { ...filters };
  let fromProfile = false;
  if (!next.game_version && profile.game_version) {
    next.game_version = profile.game_version;
    fromProfile = true;
  }
  const loader = profile.loader && profile.loader !== "vanilla" ? profile.loader : "";
  if (!next.loader && loader && next.type === "mod") {
    next.loader = loader;
    fromProfile = true;
  }
  return { filters: next, fromProfile };
}

export function toApiQuery(filters: ModFilters, page = filters.page): CatalogQuery {
  const query: CatalogQuery = { type: filters.type, page };
  if (filters.game_version) query.game_version = filters.game_version;
  if (filters.loader && filters.type === "mod") query.loader = filters.loader;
  if (filters.categories.length) query.category = filters.categories.join(",");
  if (filters.gpu_load && filters.type === "shader") {
    query.gpu_load = filters.gpu_load as CatalogQuery["gpu_load"];
  }
  if (filters.sort) query.sort = filters.sort as CatalogQuery["sort"];
  if (filters.q) query.q = filters.q;
  return query;
}

/** Link to the catalog with some filters changed; changing filters resets the page. */
export function catalogHref(filters: ModFilters, change: Partial<ModFilters> = {}): string {
  const next = { ...filters, page: 1, ...change };
  const params = new URLSearchParams();
  if (next.type !== "mod") params.set("type", next.type);
  if (next.game_version) params.set("game_version", next.game_version);
  if (next.loader && next.type === "mod") params.set("loader", next.loader);
  if (next.categories.length) params.set("category", next.categories.join(","));
  if (next.gpu_load && next.type === "shader") params.set("gpu_load", next.gpu_load);
  if (next.sort) params.set("sort", next.sort);
  if (next.q) params.set("q", next.q);
  if (next.all) params.set("all", "1");
  const query = params.toString();
  return query ? `/mods?${query}` : "/mods";
}

export function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}
