import {
  type CatalogQuery,
  type ColorBucket,
  type SkinModel,
  type Style,
  colorBuckets,
  styles,
} from "./types";

/** Catalog state, kept in the URL query string. */
export type SkinFilters = {
  color: ColorBucket | "";
  model: SkinModel | "";
  styles: Style[];
  sort: string;
  q: string;
  page: number;
};

type SearchParams = Record<string, string | string[] | undefined>;

const sorts = ["popular", "new", "top"];

const first = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() ?? "";

export function parseFilters(params: SearchParams): SkinFilters {
  const color = first(params.color) as ColorBucket;
  const model = first(params.model) as SkinModel;
  const sort = first(params.sort);
  return {
    color: colorBuckets.includes(color) ? color : "",
    model: model === "classic" || model === "slim" ? model : "",
    styles: first(params.style)
      .split(",")
      .filter((style): style is Style => styles.includes(style as Style)),
    sort: sorts.includes(sort) ? sort : "",
    q: first(params.q),
    page: Math.max(1, Number.parseInt(first(params.page), 10) || 1),
  };
}

export function toApiQuery(filters: SkinFilters, page = filters.page): CatalogQuery {
  const query: CatalogQuery = { page };
  if (filters.color) query.color = filters.color;
  if (filters.model) query.model = filters.model;
  if (filters.styles.length) query.style = filters.styles.join(",");
  if (filters.sort) query.sort = filters.sort as CatalogQuery["sort"];
  if (filters.q) query.q = filters.q;
  return query;
}

/** Link to the catalog with some filters changed; changing filters resets the page. */
export function catalogHref(filters: SkinFilters, change: Partial<SkinFilters> = {}): string {
  const next = { ...filters, page: 1, ...change };
  const params = new URLSearchParams();
  if (next.color) params.set("color", next.color);
  if (next.model) params.set("model", next.model);
  if (next.styles.length) params.set("style", next.styles.join(","));
  if (next.sort) params.set("sort", next.sort);
  if (next.q) params.set("q", next.q);
  const query = params.toString();
  return query ? `/skins?${query}` : "/skins";
}
