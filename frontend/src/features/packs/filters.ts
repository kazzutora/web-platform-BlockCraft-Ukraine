import { gameVersions } from "@/features/game/labels";

import {
  type CatalogQuery,
  type PackLoader,
  type PackStyle,
  packLoaders,
  packStyles,
} from "./types";

/** Catalog state, kept in the URL query string. */
export type PackFilters = {
  gameVersion: string;
  loader: PackLoader | "";
  styles: PackStyle[];
  official: boolean;
  sort: string;
  q: string;
  page: number;
};

type SearchParams = Record<string, string | string[] | undefined>;

const sorts = ["popular", "new", "top", "downloads"];

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export function parseFilters(params: SearchParams): PackFilters {
  const gameVersion = first(params.version);
  const loader = first(params.loader) as PackLoader;
  const sort = first(params.sort);
  return {
    gameVersion: (gameVersions as string[]).includes(gameVersion) ? gameVersion : "",
    loader: packLoaders.includes(loader) ? loader : "",
    styles: first(params.style)
      .split(",")
      .filter((style): style is PackStyle => packStyles.includes(style as PackStyle)),
    official: first(params.official) === "1",
    sort: sorts.includes(sort) ? sort : "",
    q: first(params.q),
    page: Math.max(1, Number.parseInt(first(params.page), 10) || 1),
  };
}

export function toApiQuery(filters: PackFilters, page = filters.page): CatalogQuery {
  const query: CatalogQuery = { page };
  if (filters.gameVersion) query.game_version = filters.gameVersion as CatalogQuery["game_version"];
  if (filters.loader) query.loader = filters.loader;
  if (filters.styles.length) query.style = filters.styles.join(",");
  if (filters.official) query.official = true;
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
  if (next.styles.length) params.set("style", next.styles.join(","));
  if (next.official) params.set("official", "1");
  if (next.sort) params.set("sort", next.sort);
  if (next.q) params.set("q", next.q);
  const query = params.toString();
  return query ? `/packs?${query}` : "/packs";
}

export function toggleStyle(list: PackStyle[], style: PackStyle): PackStyle[] {
  return list.includes(style) ? list.filter((item) => item !== style) : [...list, style];
}
