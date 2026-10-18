import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { gameVersions, loaderOptions } from "@/features/game/labels";

import { modsCopy } from "./copy";
import { type ModFilters, catalogHref, toggle } from "./filters";
import { NavigateSelect } from "@/components/ui/NavigateSelect";
import { type Category, projectTypes } from "./types";

const copy = modsCopy.filters;
const modLoaders = loaderOptions.filter((option) => option.value !== "vanilla");

type CatalogFiltersProps = {
  filters: ModFilters;
  categories: Category[];
  fromProfile: boolean;
};

/** Filter rows of the catalog; every chip is a link to the same page with other filters. */
export function CatalogFilters({ filters, categories, fromProfile }: CatalogFiltersProps) {
  const versionOptions = [
    {
      value: "",
      label: copy.allVersions,
      href: catalogHref(filters, { game_version: "", all: true }),
    },
    ...gameVersions.map((version) => ({
      value: version,
      label: version,
      href: catalogHref(filters, { game_version: version }),
    })),
  ];
  const sortOptions = copy.sorts.map((sort) => ({
    ...sort,
    href: catalogHref(filters, { sort: sort.value === "popular" ? "" : sort.value }),
  }));
  const shownCategories = categories.filter((category) => category.header !== "performance impact");

  return (
    <div className="flex flex-col gap-4">
      <FilterRow label={copy.typeLabel}>
        {projectTypes.map((type) => (
          <FilterChip
            key={type}
            href={catalogHref(filters, { type, categories: [], gpu_load: "" })}
            active={filters.type === type}
          >
            {modsCopy.types[type].title}
          </FilterChip>
        ))}
      </FilterRow>

      <div className="flex flex-col gap-3 sm:flex-row">
        <NavigateSelect
          label={copy.version}
          value={filters.game_version}
          options={versionOptions}
        />
        <NavigateSelect label={copy.sort} value={filters.sort || "popular"} options={sortOptions} />
      </div>

      {filters.type === "mod" && (
        <FilterRow label={copy.loaderLabel}>
          {modLoaders.map((loader) => (
            <FilterChip
              key={loader.value}
              href={catalogHref(filters, {
                loader: filters.loader === loader.value ? "" : loader.value,
                all: filters.loader === loader.value ? true : filters.all,
              })}
              active={filters.loader === loader.value}
            >
              {loader.label}
            </FilterChip>
          ))}
        </FilterRow>
      )}

      {filters.type === "shader" && (
        <FilterRow label={copy.gpuLabel}>
          {(["light", "medium", "heavy"] as const).map((load) => (
            <FilterChip
              key={load}
              href={catalogHref(filters, { gpu_load: filters.gpu_load === load ? "" : load })}
              active={filters.gpu_load === load}
            >
              {copy.gpu[load]}
            </FilterChip>
          ))}
        </FilterRow>
      )}

      {shownCategories.length > 0 && (
        <FilterRow label={copy.categoriesLabel}>
          {shownCategories.map((category) => (
            <FilterChip
              key={category.slug}
              href={catalogHref(filters, {
                categories: toggle(filters.categories, category.slug),
              })}
              active={filters.categories.includes(category.slug)}
            >
              {category.name}
            </FilterChip>
          ))}
        </FilterRow>
      )}

      {fromProfile && (
        <p className="flex flex-wrap items-center gap-3 text-meta text-muted">
          {copy.fromProfile}
          <FilterChip
            href={catalogHref(filters, { game_version: "", loader: "", all: true })}
            active={false}
          >
            {copy.showAll}
          </FilterChip>
        </p>
      )}
    </div>
  );
}
