import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { NavigateSelect } from "@/components/ui/NavigateSelect";
import { gameCopy } from "@/features/game/copy";

import { packsCopy } from "./copy";
import { type PackFilters as Filters, type PackOrigin, catalogHref } from "./filters";
import { packLoaders } from "./types";

const copy = packsCopy.filters;
const origins: PackOrigin[] = ["modrinth", "community"];

type PackFiltersProps = {
  filters: Filters;
  gameVersions: string[];
  /** Version and loader came from «Моя гра»: offer to show everything. */
  fromGame: boolean;
  inviteToChoose: boolean;
};

/** Version, sort, loader and origin: every chip is a link with the other filters kept. */
export function PackFilters({ filters, gameVersions, fromGame, inviteToChoose }: PackFiltersProps) {
  const versionOptions = [
    {
      value: "",
      label: copy.allVersions,
      href: catalogHref(filters, { gameVersion: "", all: true }),
    },
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
        <FilterChip href={catalogHref(filters, { loader: "", all: true })} active={!filters.loader}>
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
      </FilterRow>
      <FilterRow label={copy.origin}>
        <FilterChip href={catalogHref(filters, { origin: "" })} active={!filters.origin}>
          {copy.anyOrigin}
        </FilterChip>
        {origins.map((origin) => (
          <FilterChip
            key={origin}
            href={catalogHref(filters, { origin: filters.origin === origin ? "" : origin })}
            active={filters.origin === origin}
          >
            {packsCopy.origins[origin]}
          </FilterChip>
        ))}
      </FilterRow>
      {inviteToChoose && <p className="text-meta text-muted">{gameCopy.invite}</p>}
      {fromGame && (
        <p className="flex flex-wrap items-center gap-3 text-meta text-muted">
          {copy.fromProfile}
          <FilterChip
            href={catalogHref(filters, { gameVersion: "", loader: "", all: true })}
            active={false}
          >
            {copy.showAll}
          </FilterChip>
        </p>
      )}
    </div>
  );
}
