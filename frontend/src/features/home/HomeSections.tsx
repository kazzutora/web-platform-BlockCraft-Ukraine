import Link from "next/link";
import type { ReactNode } from "react";

import { ButtonLink } from "@/components/ui/ButtonLink";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { gameName } from "@/features/game/labels";
import { ModCard } from "@/features/mods/ModCard";
import { PackCard } from "@/features/packs/PackCard";
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

/** Everything under the hero, in the order of tech.md 10.4. */
export async function HomeSections() {
  const home = await getHome();
  const forYou = home.for_you;
  const personal = forYou.basis === "profile";
  // Only «Без модів» chosen: «Популярне для гри без модів»
  const game = !personal
    ? ""
    : forYou.game_version || forYou.loader !== "vanilla"
      ? gameName(forYou)
      : copy.vanillaGame;
  const skin = home.skin_of_day;

  return (
    <div className="flex flex-col gap-28 md:gap-36">
      <Section
        title={personal ? copy.forYou(game) : copy.popular}
        link={{ href: "/mods", label: copy.allMods }}
      >
        {!personal && <p className="-mt-4 max-w-prose text-muted">{copy.invite}</p>}
        {forYou.mods.length ? (
          <CardGrid>
            {forYou.mods.map((project, index) => (
              <ModCard key={project.slug} project={project} eager={index < 4} gameLabel={game} />
            ))}
          </CardGrid>
        ) : (
          <EmptyState
            title={personal ? copy.empty : copy.emptyPopular}
            illustration="mods"
            action={
              <ButtonLink href="/mods?all=1" variant="secondary">
                {copy.allVersionsMods}
              </ButtonLink>
            }
          />
        )}
      </Section>

      <Section title={copy.packs} link={{ href: "/packs", label: copy.allPacks }}>
        {home.packs.length ? (
          <CardGrid>
            {home.packs.map((pack) => (
              <PackCard key={pack.slug} pack={pack} gameLabel={game} />
            ))}
          </CardGrid>
        ) : (
          <EmptyState
            title={personal ? copy.noPacks(game) : copy.noPacksAtAll}
            illustration="packs"
            action={
              <ButtonLink href="/packs?all=1" variant="secondary">
                {copy.allVersionsPacks}
              </ButtonLink>
            }
          />
        )}
      </Section>

      <section className="flex flex-col gap-6 border border-line bg-surface p-8 md:flex-row md:items-center md:justify-between md:p-12">
        <div className="flex max-w-prose flex-col gap-3">
          <h2 className="text-h2">{copy.check.title}</h2>
          <p className="text-muted">{copy.check.text}</p>
        </div>
        <ButtonLink
          href="/import"
          variant="secondary"
          size="lg"
          className="self-start md:self-auto"
        >
          {copy.check.action}
        </ButtonLink>
      </section>

      <Section
        title={copy.serversOnline}
        link={{ href: "/servers?online=1&sort=online&language=uk", label: copy.allServers }}
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

      {skin && (
        <Section title={copy.skinOfDay} link={{ href: "/skins", label: copy.allSkins }}>
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
                {skin.source.name} · {skinsCopy.models[skin.model]}
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
          {home.skins.length > 0 && (
            <CardGrid>
              {home.skins.map((item) => (
                <SkinCard key={item.id} skin={item} />
              ))}
            </CardGrid>
          )}
        </Section>
      )}
    </div>
  );
}
