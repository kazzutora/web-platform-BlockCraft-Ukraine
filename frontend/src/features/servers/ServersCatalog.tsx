import { CatalogPage } from "@/components/layout/CatalogPage";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { plural } from "@/lib/plural";

import { getCatalog } from "./api";
import { serversCopy } from "./copy";
import { type ServerFilters as Filters, toApiQuery } from "./filters";
import { LoadMoreServers } from "./LoadMoreServers";
import { ServerFilters } from "./ServerFilters";
import { ServerRow } from "./ServerRow";

/** /servers: rows with live online; filters live in the URL. */
export async function ServersCatalog({ filters }: { filters: Filters }) {
  const query = toApiQuery(filters);
  const page = await getCatalog(query);

  return (
    <CatalogPage
      illustration="servers"
      title={serversCopy.title}
      count={plural(page.count, serversCopy.plural)}
      filters={
        <div className="flex flex-col gap-6">
          <div>
            <ButtonLink href="/servers/new">
              <Icon name="plus" />
              {serversCopy.add}
            </ButtonLink>
          </div>
          <ServerFilters filters={filters} />
        </div>
      }
      footer={
        page.next ? (
          <LoadMoreServers key={JSON.stringify(query)} query={query} startPage={filters.page + 1} />
        ) : null
      }
    >
      {page.results.length ? (
        <ul className="flex flex-col border-t border-line">
          {page.results.map((server) => (
            <ServerRow key={server.slug} server={server} />
          ))}
        </ul>
      ) : (
        <EmptyState title={serversCopy.empty} illustration="empty" />
      )}
    </CatalogPage>
  );
}
