import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { NavigateSelect } from "@/components/ui/NavigateSelect";

import { serversCopy } from "./copy";
import { type ServerFilters as Filters, catalogHref, toggleMode } from "./filters";
import { editions, languages, modes } from "./types";

const copy = serversCopy.filters;

/** Mode, edition and language chips, «зараз онлайн», sorting: every one is a link. */
export function ServerFilters({ filters }: { filters: Filters }) {
  const sortOptions = copy.sorts.map((sort) => ({
    ...sort,
    href: catalogHref(filters, { sort: sort.value === "popular" ? "" : sort.value }),
  }));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <FilterRow label={copy.online}>
          <FilterChip
            href={catalogHref(filters, { online: !filters.online })}
            active={filters.online}
          >
            <span aria-hidden className="size-2.5 bg-accent" />
            {copy.online}
          </FilterChip>
          <FilterChip
            href={catalogHref(filters, { whitelist: !filters.whitelist })}
            active={filters.whitelist}
          >
            {copy.whitelist}
          </FilterChip>
        </FilterRow>
        <NavigateSelect label={copy.sort} value={filters.sort || "popular"} options={sortOptions} />
      </div>

      <FilterRow label={copy.mode}>
        {modes.map((mode) => (
          <FilterChip
            key={mode}
            href={catalogHref(filters, { modes: toggleMode(filters.modes, mode) })}
            active={filters.modes.includes(mode)}
          >
            {serversCopy.modes[mode]}
          </FilterChip>
        ))}
      </FilterRow>

      <FilterRow label={copy.edition}>
        <FilterChip href={catalogHref(filters, { edition: "" })} active={!filters.edition}>
          {copy.anyEdition}
        </FilterChip>
        {editions
          .filter((edition) => edition !== "both")
          .map((edition) => (
            <FilterChip
              key={edition}
              href={catalogHref(filters, { edition: filters.edition === edition ? "" : edition })}
              active={filters.edition === edition}
            >
              {serversCopy.editions[edition]}
            </FilterChip>
          ))}
        <span aria-hidden className="mx-2 w-px shrink-0 bg-line" />
        <FilterChip href={catalogHref(filters, { language: "" })} active={!filters.language}>
          {copy.anyLanguage}
        </FilterChip>
        {languages.map((language) => (
          <FilterChip
            key={language}
            href={catalogHref(filters, {
              language: filters.language === language ? "" : language,
            })}
            active={filters.language === language}
          >
            {serversCopy.languages[language]}
          </FilterChip>
        ))}
      </FilterRow>
    </div>
  );
}
