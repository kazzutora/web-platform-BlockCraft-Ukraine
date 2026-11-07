import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { NavigateSelect } from "@/components/ui/NavigateSelect";

import { packsCopy } from "./copy";
import { type PackFilters as Filters, catalogHref, toggleStyle } from "./filters";
import { packLoaders, packStyles } from "./types";

const copy = packsCopy.filters;

/** Version, sort, loader and style: every chip is a link with the other filters kept. */
export function PackFilters({
  filters,
  gameVersions,
}: {
  filters: Filters;
  gameVersions: string[];
}) {
  const versionOptions = [
    { value: "", label: copy.allVersions, href: catalogHref(filters, { gameVersion: "" }) },
    ...gameVersions.map((version) => ({
      value: version,
      label: version,
      href: catalogHref(filters, { gameVersion: version }),
    })),
  ];
  const sortOptions = copy.sorts.map((sort) => ({
    ...sort,
    href: catalogHref(filters, { sort: sort.value === "popular" ? "" : sort.value }),
  }));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <NavigateSelect label={copy.version} value={filters.gameVersion} options={versionOptions} />
        <NavigateSelect label={copy.sort} value={filters.sort || "popular"} options={sortOptions} />
      </div>
      <FilterRow label={copy.loader}>
        <FilterChip href={catalogHref(filters, { loader: "" })} active={!filters.loader}>
          {copy.anyLoader}
        </FilterChip>
        {packLoaders.map((loader) => (
          <FilterChip
            key={loader}
            href={catalogHref(filters, { loader: filters.loader === loader ? "" : loader })}
            active={filters.loader === loader}
          >
            {packsCopy.loaders[loader]}
          </FilterChip>
        ))}
        <FilterChip
          href={catalogHref(filters, { official: !filters.official })}
          active={filters.official}
        >
          {copy.official}
        </FilterChip>
      </FilterRow>
      <FilterRow label={copy.style}>
        {packStyles.map((style) => (
          <FilterChip
            key={style}
            href={catalogHref(filters, { styles: toggleStyle(filters.styles, style) })}
            active={filters.styles.includes(style)}
          >
            {packsCopy.styles[style]}
          </FilterChip>
        ))}
      </FilterRow>
    </div>
  );
}
