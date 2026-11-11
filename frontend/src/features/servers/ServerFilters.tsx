import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { NavigateSelect } from "@/components/ui/NavigateSelect";

import { countryName, languageName, serversCopy } from "./copy";
import {
  ALL_LANGUAGES,
  type ServerFilters as Filters,
  catalogHref,
  effectiveLanguage,
  toggle,
} from "./filters";
import { type ServerCategory, contentKinds } from "./types";

const copy = serversCopy.filters;
/** Shown as chips; the rest of the languages are in the select. */
const LANGUAGE_CHIPS = ["uk", "en"];
/** Modes as chips: the gameplay group of Modrinth categories. */
const MODE_HEADER = "minecraft_server_gameplay";

type ServerFiltersProps = {
  filters: Filters;
  defaultLanguage: string;
  languages: string[];
  countries: string[];
  versions: string[];
  categories: ServerCategory[];
};

/** Language, what is needed to join, online, country, version, mode, sorting: all links. */
export function ServerFilters({
  filters,
  defaultLanguage,
  languages,
  countries,
  versions,
  categories,
}: ServerFiltersProps) {
  const language = effectiveLanguage(filters, defaultLanguage);
  const otherLanguages = languages.filter((code) => !LANGUAGE_CHIPS.includes(code));
  const sortOptions = copy.sorts.map((sort) => ({
    ...sort,
    href: catalogHref(filters, { sort: sort.value === "popular" ? "" : sort.value }),
  }));
  const countryOptions = [
    { value: "", label: copy.anyCountry, href: catalogHref(filters, { country: "" }) },
    ...countries
      .map((code) => ({ value: code, label: countryName(code) }))
      .sort((a, b) => a.label.localeCompare(b.label, "uk"))
      .map((option) => ({ ...option, href: catalogHref(filters, { country: option.value }) })),
  ];
  const versionOptions = [
    { value: "", label: copy.anyVersion, href: catalogHref(filters, { version: "" }) },
    ...versions.map((version) => ({
      value: version,
      label: version,
      href: catalogHref(filters, { version }),
    })),
  ];
  const languageOptions = otherLanguages
    .map((code) => ({ value: code, label: languageName(code) }))
    .sort((a, b) => a.label.localeCompare(b.label, "uk"))
    .map((option) => ({ ...option, href: catalogHref(filters, { language: option.value }) }));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <FilterRow label={copy.language}>
          {LANGUAGE_CHIPS.map((code) => (
            <FilterChip
              key={code}
              href={catalogHref(filters, { language: code })}
              active={language === code}
            >
              {languageName(code)}
            </FilterChip>
          ))}
          <FilterChip href={catalogHref(filters, { language: ALL_LANGUAGES })} active={!language}>
            {copy.allLanguages}
          </FilterChip>
        </FilterRow>
        {languageOptions.length > 0 && (
          <NavigateSelect
            label={copy.language}
            value={otherLanguages.includes(language) ? language : ""}
            placeholder={copy.language}
            options={languageOptions}
          />
        )}
      </div>

      <FilterRow label={copy.kind}>
        <FilterChip
          href={catalogHref(filters, { online: !filters.online })}
          active={filters.online}
        >
          <span aria-hidden className="size-2.5 bg-accent" />
          {copy.online}
        </FilterChip>
        <span aria-hidden className="mx-2 w-px shrink-0 bg-line" />
        {contentKinds.map((kind) => (
          <FilterChip
            key={kind}
            href={catalogHref(filters, { kind: filters.kind === kind ? "" : kind })}
            active={filters.kind === kind}
          >
            {serversCopy.kinds[kind]}
          </FilterChip>
        ))}
      </FilterRow>

      <FilterRow label={copy.category}>
        {categories
          .filter((category) => category.header === MODE_HEADER)
          .map((category) => (
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

      <div className="flex flex-col gap-3 sm:flex-row">
        <NavigateSelect label={copy.country} value={filters.country} options={countryOptions} />
        <NavigateSelect label={copy.version} value={filters.version} options={versionOptions} />
        <NavigateSelect label={copy.sort} value={filters.sort || "popular"} options={sortOptions} />
      </div>
    </div>
  );
}
