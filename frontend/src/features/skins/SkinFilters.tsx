import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { NavigateSelect } from "@/components/ui/NavigateSelect";
import { cn } from "@/lib/cn";

import { skinsCopy } from "./copy";
import { type SkinFilters as Filters, catalogHref } from "./filters";
import { type ColorBucket, colorBuckets, skinSources } from "./types";

const copy = skinsCopy.filters;

const swatches: Record<ColorBucket, string> = {
  red: "bg-swatch-red",
  orange: "bg-swatch-orange",
  yellow: "bg-swatch-yellow",
  green: "bg-swatch-green",
  cyan: "bg-swatch-cyan",
  blue: "bg-swatch-blue",
  purple: "bg-swatch-purple",
  pink: "bg-swatch-pink",
  brown: "bg-swatch-brown",
  black: "bg-swatch-black",
  white: "bg-swatch-white",
  gray: "bg-swatch-gray",
};

/** Colour squares, model and source chips: every one is a link with other filters. */
export function SkinFilters({ filters }: { filters: Filters }) {
  const sortOptions = copy.sorts.map((sort) => ({
    ...sort,
    href: catalogHref(filters, { sort: sort.value === "popular" ? "" : sort.value }),
  }));

  return (
    <div className="flex flex-col gap-4">
      <div role="group" aria-label={copy.color} className="flex flex-wrap gap-2">
        {colorBuckets.map((color) => {
          const active = filters.color === color;
          return (
            <FilterChip
              key={color}
              href={catalogHref(filters, { color: active ? "" : color })}
              active={active}
              className="size-11 justify-center px-0"
            >
              <span aria-hidden className={cn("size-6 border border-line", swatches[color])} />
              <span className="sr-only">{skinsCopy.colors[color]}</span>
            </FilterChip>
          );
        })}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <FilterRow label={copy.model}>
          <FilterChip href={catalogHref(filters, { model: "" })} active={!filters.model}>
            {copy.anyModel}
          </FilterChip>
          {(["classic", "slim"] as const).map((model) => (
            <FilterChip
              key={model}
              href={catalogHref(filters, { model: filters.model === model ? "" : model })}
              active={filters.model === model}
            >
              {skinsCopy.models[model]}
            </FilterChip>
          ))}
        </FilterRow>
        <NavigateSelect label={copy.sort} value={filters.sort || "popular"} options={sortOptions} />
      </div>

      <FilterRow label={copy.source}>
        <FilterChip href={catalogHref(filters, { source: "" })} active={!filters.source}>
          {copy.anySource}
        </FilterChip>
        {skinSources.map((source) => (
          <FilterChip
            key={source}
            href={catalogHref(filters, { source: filters.source === source ? "" : source })}
            active={filters.source === source}
          >
            {skinsCopy.sources[source]}
          </FilterChip>
        ))}
      </FilterRow>
    </div>
  );
}
