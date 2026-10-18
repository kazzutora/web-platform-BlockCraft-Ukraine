import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { ModCard } from "@/features/mods/ModCard";
import { ServerRow } from "@/features/servers/ServerRow";
import { SkinCard } from "@/features/skins/SkinCard";
import { getServerClient } from "@/lib/api/server-client";

export type TopKind = "mod" | "skin" | "server";
export type TopPeriod = "week" | "month" | "all";

export const topCopy = {
  title: "Топи",
  kindLabel: "Розділ",
  periodLabel: "Період",
  kinds: { mod: "Моди", skin: "Скіни", server: "Сервери" } satisfies Record<TopKind, string>,
  periods: { week: "Тиждень", month: "Місяць", all: "Увесь час" } satisfies Record<
    TopPeriod,
    string
  >,
  empty: "За цей період ще нічого не набрало вподобань. Спробуй інший період.",
};

function href(kind: TopKind, period: TopPeriod): string {
  const params = new URLSearchParams();
  if (kind !== "mod") params.set("kind", kind);
  if (period !== "week") params.set("period", period);
  const query = params.toString();
  return query ? `/top?${query}` : "/top";
}

/** /top: the section and period switchers, then cards (rows for servers). */
export async function TopList({ kind, period }: { kind: TopKind; period: TopPeriod }) {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/top", { params: { query: { kind, period } } });
  const empty = !data || !(data.mods.length || data.skins.length || data.servers.length);

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-4">
        <FilterRow label={topCopy.kindLabel}>
          {(Object.keys(topCopy.kinds) as TopKind[]).map((name) => (
            <FilterChip key={name} href={href(name, period)} active={kind === name}>
              {topCopy.kinds[name]}
            </FilterChip>
          ))}
        </FilterRow>
        <FilterRow label={topCopy.periodLabel}>
          {(Object.keys(topCopy.periods) as TopPeriod[]).map((name) => (
            <FilterChip key={name} href={href(kind, name)} active={period === name}>
              {topCopy.periods[name]}
            </FilterChip>
          ))}
        </FilterRow>
      </div>

      {empty ? (
        <EmptyState title={topCopy.empty} illustration="empty" />
      ) : kind === "server" ? (
        <ol className="flex flex-col border-t border-line">
          {data.servers.map((server) => (
            <ServerRow key={server.slug} server={server} />
          ))}
        </ol>
      ) : (
        <CardGrid>
          {kind === "mod"
            ? data.mods.map((project, index) => (
                <ModCard key={project.slug} project={project} eager={index < 4} />
              ))
            : data.skins.map((skin, index) => (
                <SkinCard key={skin.id} skin={skin} eager={index < 4} />
              ))}
        </CardGrid>
      )}
    </div>
  );
}
