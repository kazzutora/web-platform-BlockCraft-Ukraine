import { CatalogPage } from "@/components/layout/CatalogPage";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { getMeta } from "@/features/game/meta";
import { plural } from "@/lib/plural";

import { getCatalog } from "./api";
import { serversCopy } from "./copy";
import { type ServerFilters as Filters, toApiQuery } from "./filters";
import { LoadMoreServers } from "./LoadMoreServers";
import { ServerFilters } from "./ServerFilters";
import { ServerRow } from "./ServerRow";

/** /servers: real servers with live online; filters live in the URL. */
export async function ServersCatalog({ filters }: { filters: Filters }) {
  const meta = await getMeta();
  const query = toApiQuery(filters, meta.server_default_language);
  const page = await getCatalog(query);

  return (
    <CatalogPage
      illustration="servers"
      title={serversCopy.title}
      count={plural(page.count, serversCopy.plural)}
      filters={
        <div className="flex flex-col gap-6">
          <p className="max-w-prose text-muted">{serversCopy.description}</p>
          <ServerFilters
            filters={filters}
            defaultLanguage={meta.server_default_language}
            languages={meta.server_languages}
            countries={meta.server_countries}
            versions={meta.game_versions.map((item) => item.version)}
            categories={meta.server_categories}
          />
        </div>
      }
      footer={
        <div className="flex flex-col gap-10">
          {page.next ? (
            <LoadMoreServers
              key={JSON.stringify(query)}
              query={query}
              startPage={filters.page + 1}
              categories={meta.server_categories}
            />
          ) : null}
          <div className="flex flex-col items-start gap-3 border-t border-line pt-8">
            <p className="text-muted">{serversCopy.addForm.lead}</p>
            <ButtonLink href="/servers/add" variant="secondary">
              <Icon name="plus" />
              {serversCopy.add}
            </ButtonLink>
          </div>
        </div>
      }
    >
      {page.results.length ? (
        <ul className="flex flex-col border-t border-line">
          {page.results.map((server) => (
            <ServerRow key={server.slug} server={server} categories={meta.server_categories} />
          ))}
        </ul>
      ) : (
        <EmptyState title={serversCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
