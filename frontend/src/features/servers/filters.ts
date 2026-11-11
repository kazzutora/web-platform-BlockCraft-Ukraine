import { type CatalogQuery, type ContentKind, contentKinds } from "./types";

/** Catalog state, kept in the URL query string. */
export type ServerFilters = {
  /** null — not in the URL: the catalog default («uk» while there are enough such servers). */
  language: string | null;
  country: string;
  kind: ContentKind | "";
  version: string;
  categories: string[];
  online: boolean;
  sort: string;
  q: string;
  page: number;
};

type SearchParams = Record<string, string | string[] | undefined>;

const sorts = ["popular", "online", "new", "top"];
/** «Усі мови» in the URL. */
export const ALL_LANGUAGES = "all";

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

function parseLanguage(params: SearchParams): string | null {
  if (params.language === undefined) return null;
  const language = first(params.language).toLowerCase();
  return /^[a-z]{2,3}$/.test(language) ? language : ALL_LANGUAGES;
}

export function parseFilters(params: SearchParams): ServerFilters {
  const kind = first(params.kind) as ContentKind;
  const sort = first(params.sort);
  const country = first(params.country).toUpperCase();
  return {
    language: parseLanguage(params),
    country: /^[A-Z]{2}$/.test(country) ? country : "",
    kind: contentKinds.includes(kind) ? kind : "",
    version: first(params.version).slice(0, 32),
    categories: first(params.category)
      .split(",")
      .map((item) => item.trim())
      .filter((item) => /^[a-z0-9-]{1,48}$/.test(item)),
    online: first(params.online) === "1",
    sort: sorts.includes(sort) ? sort : "",
    q: first(params.q),
    page: Math.max(1, Number.parseInt(first(params.page), 10) || 1),
  };
}

/** The language the catalog shows: from the URL, otherwise the default from /meta. */
export function effectiveLanguage(filters: ServerFilters, fallback: string): string {
  if (filters.language === null) return fallback;
  return filters.language === ALL_LANGUAGES ? "" : filters.language;
}

/** The API always gets the language explicitly: no filter the player cannot see. */
export function toApiQuery(
  filters: ServerFilters,
  defaultLanguage: string,
  page = filters.page,
): CatalogQuery {
  const query: CatalogQuery = { page, language: effectiveLanguage(filters, defaultLanguage) };
  if (filters.country) query.country = filters.country;
  if (filters.kind) query.kind = filters.kind;
  if (filters.version) query.version = filters.version;
  if (filters.categories.length) query.category = filters.categories.join(",");
  if (filters.online) query.online = true;
  if (filters.sort) query.sort = filters.sort as CatalogQuery["sort"];
  if (filters.q) query.q = filters.q;
  return query;
}

/** Link to the catalog with some filters changed; changing filters resets the page. */
export function catalogHref(filters: ServerFilters, change: Partial<ServerFilters> = {}): string {
  const next = { ...filters, page: 1, ...change };
  const params = new URLSearchParams();
  if (next.language !== null) params.set("language", next.language);
  if (next.country) params.set("country", next.country);
  if (next.kind) params.set("kind", next.kind);
  if (next.version) params.set("version", next.version);
  if (next.categories.length) params.set("category", next.categories.join(","));
  if (next.online) params.set("online", "1");
  if (next.sort) params.set("sort", next.sort);
  if (next.q) params.set("q", next.q);
  const query = params.toString();
  return query ? `/servers?${query}` : "/servers";
}

export function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}
