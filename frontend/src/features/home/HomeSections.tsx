import Link from "next/link";
import type { ReactNode } from "react";

import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { loaderName } from "@/features/mods/format";
import { ModCard } from "@/features/mods/ModCard";
import { ServerRow } from "@/features/servers/ServerRow";
import { SkinCard } from "@/features/skins/SkinCard";
import { SkinViewer } from "@/features/skins/SkinViewer";
import { skinsCopy } from "@/features/skins/copy";

import { getHome } from "./api";
import { homeCopy as copy } from "./copy";

function Section({
  title,
  link,
  children,
}: {
  title: string;
  link?: { href: string; label: string };
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-wrap items-baseline justify-between gap-4 border-b border-line pb-4">
        <h2 className="caps font-sans">{title}</h2>
        {link && (
          <Link
            href={link.href}
            className="inline-flex items-center gap-1 text-sm underline-offset-4 hover:underline"
          >
            {link.label}
            <Icon name="chevron-right" size={16} />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

/** Everything under the hero: for your version, skin of the week, servers online, new. */
export async function HomeSections() {
  const home = await getHome();
  const forYou = home.for_you;
  const skin = home.skin_of_week;

  return (
    <div className="flex flex-col gap-28 md:gap-36">
      <Section
        title={
          forYou.basis === "profile"
            ? copy.forYou(forYou.game_version, forYou.loader ? loaderName(forYou.loader) : "")
            : copy.popular
        }
        link={{ href: "/mods", label: copy.allMods }}
      >
        {forYou.mods.length ? (
          <CardGrid>
            {forYou.mods.map((project, index) => (
              <ModCard key={project.slug} project={project} eager={index < 4} />
            ))}
          </CardGrid>
        ) : (
          <EmptyState title={copy.empty} illustration="mods" />
        )}
      </Section>

      {skin && (
        <Section title={copy.skinOfWeek} link={{ href: "/skins", label: copy.allSkins }}>
          <div className="grid gap-10 md:grid-cols-2 md:items-center md:gap-16">
            <div className="relative aspect-square border border-line bg-surface">
              <SkinViewer
                texture={skin.texture_url}
                model={skin.model}
                title={skin.title}
                fallback={skin.preview_url}
                poses={false}
              />
            </div>
            <div className="flex flex-col gap-4">
              <p className="text-h1">{skin.title}</p>
              <p className="text-muted">
                {copy.skinBy(skin.author.nickname)} · {skinsCopy.models[skin.model]}
              </p>
              <Link
                href={`/skins/${skin.id}`}
                className="inline-flex items-center gap-2 self-start border border-text px-6 py-3 font-medium hover:bg-text hover:text-bg"
              >
                {copy.openSkin}
                <Icon name="chevron-right" size={16} />
              </Link>
            </div>
          </div>
        </Section>
      )}

      <Section
        title={copy.serversOnline}
        link={{ href: "/servers?online=1&sort=online", label: copy.allServers }}
      >
        {home.servers_online.length ? (
          <ul className="flex flex-col">
            {home.servers_online.map((server) => (
              <ServerRow key={server.slug} server={server} />
            ))}
          </ul>
        ) : (
          <p className="text-muted">{copy.noServers}</p>
        )}
      </Section>

      {(home.new_skins.length > 0 || home.new_servers.length > 0) && (
        <Section title={copy.fresh} link={{ href: "/top", label: copy.top }}>
          <div className="flex flex-col gap-10">
            {home.new_skins.length > 0 && (
              <CardGrid>
                {home.new_skins.map((item) => (
                  <SkinCard key={item.id} skin={item} />
                ))}
              </CardGrid>
            )}
            {home.new_servers.length > 0 && (
              <ul className="flex flex-col border-t border-line">
                {home.new_servers.map((server) => (
                  <ServerRow key={server.slug} server={server} />
                ))}
              </ul>
            )}
          </div>
        </Section>
      )}
    </div>
  );
}
