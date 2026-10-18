import {
  type CatalogQuery,
  type Edition,
  type Language,
  type Mode,
  editions,
  languages,
  modes,
} from "./types";

/** Catalog state, kept in the URL query string. */
export type ServerFilters = {
  modes: Mode[];
  edition: Edition | "";
  language: Language | "";
  online: boolean;
  whitelist: boolean;
  sort: string;
  q: string;
  page: number;
};

type SearchParams = Record<string, string | string[] | undefined>;

const sorts = ["popular", "online", "new", "top"];

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export function parseFilters(params: SearchParams): ServerFilters {
  const edition = first(params.edition) as Edition;
  const language = first(params.language) as Language;
  const sort = first(params.sort);
  return {
    modes: first(params.mode)
      .split(",")
      .filter((mode): mode is Mode => modes.includes(mode as Mode)),
    edition: editions.includes(edition) ? edition : "",
    language: languages.includes(language) ? language : "",
    online: first(params.online) === "1",
    whitelist: first(params.whitelist) === "1",
    sort: sorts.includes(sort) ? sort : "",
    q: first(params.q),
    page: Math.max(1, Number.parseInt(first(params.page), 10) || 1),
  };
}

export function toApiQuery(filters: ServerFilters, page = filters.page): CatalogQuery {
  const query: CatalogQuery = { page };
  if (filters.modes.length) query.mode = filters.modes.join(",");
  if (filters.edition) query.edition = filters.edition;
  if (filters.language) query.language = filters.language;
  if (filters.online) query.online = true;
  if (filters.whitelist) query.whitelist = true;
  if (filters.sort) query.sort = filters.sort as CatalogQuery["sort"];
  if (filters.q) query.q = filters.q;
  return query;
}

/** Link to the catalog with some filters changed; changing filters resets the page. */
export function catalogHref(filters: ServerFilters, change: Partial<ServerFilters> = {}): string {
  const next = { ...filters, page: 1, ...change };
  const params = new URLSearchParams();
  if (next.modes.length) params.set("mode", next.modes.join(","));
  if (next.edition) params.set("edition", next.edition);
  if (next.language) params.set("language", next.language);
  if (next.online) params.set("online", "1");
  if (next.whitelist) params.set("whitelist", "1");
  if (next.sort) params.set("sort", next.sort);
  if (next.q) params.set("q", next.q);
  const query = params.toString();
  return query ? `/servers?${query}` : "/servers";
}

export function toggleMode(list: Mode[], mode: Mode): Mode[] {
  return list.includes(mode) ? list.filter((item) => item !== mode) : [...list, mode];
}
