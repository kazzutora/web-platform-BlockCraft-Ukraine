import { Container } from "@/components/layout/Container";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Tabs } from "@/components/ui/Tabs";
import { CollectionCard } from "@/features/library/CollectionCard";
import { SkinCard } from "@/features/skins/SkinCard";

import { type PublicProfile, getProfileWorks } from "./api";
import { ProfileSkin } from "./ProfileSkin";

const copy = {
  level: (level: number) => `Рівень ${level}`,
  since: (date: string) =>
    `З нами з ${new Date(date).toLocaleDateString("uk-UA", { month: "long", year: "numeric" })}`,
  private: "Закритий профіль",
  privateText: "Гравець вирішив не показувати свій профіль.",
  tabsLabel: "Розділи профілю",
  tabs: { works: "Скіни", collections: "Колекції", setup: "Сетап" },
  empty: {
    works: "Гравець ще не опублікував жодного скіна.",
    collections: "Публічних колекцій поки немає.",
    setup: "Сетап — версія, моди й скін — з’явиться пізніше.",
  },
};

export async function ProfileView({ profile }: { profile: PublicProfile }) {
  if (profile.is_private && profile.level === null) {
    return (
      <Container className="flex flex-col items-start gap-6 py-12 md:py-16">
        <Avatar name={profile.nickname} size={128} />
        <h1 className="text-h1">{profile.nickname}</h1>
        <Badge icon="lock">{copy.private}</Badge>
        <p className="text-muted">{copy.privateText}</p>
      </Container>
    );
  }

  const works = await getProfileWorks(profile.nickname);

  return (
    <Container className="flex flex-col gap-16 py-12 md:py-16">
      <header className="flex flex-col gap-10 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:gap-10">
          <Avatar name={profile.nickname} src={profile.avatar_url} size={128} />
          <div className="flex flex-col gap-3">
            <h1 className="text-h1">{profile.nickname}</h1>
            <div className="flex flex-wrap items-center gap-3">
              {profile.level !== null && <Badge tone="accent">{copy.level(profile.level)}</Badge>}
              {profile.is_private && <Badge icon="lock">{copy.private}</Badge>}
              {profile.date_joined && (
                <span className="text-meta text-muted">{copy.since(profile.date_joined)}</span>
              )}
            </div>
            {profile.bio && <p className="max-w-prose">{profile.bio}</p>}
          </div>
        </div>
        <ProfileSkin
          nickname={profile.nickname}
          skin={profile.skin}
          mcNickname={profile.mc_nickname}
        />
      </header>
      <Tabs
        label={copy.tabsLabel}
        items={[
          {
            value: "works",
            label: works.skins.length
              ? `${copy.tabs.works} · ${works.skins.length}`
              : copy.tabs.works,
            content: works.skins.length ? (
              <CardGrid>
                {works.skins.map((skin, index) => (
                  <SkinCard key={skin.id} skin={skin} eager={index < 4} />
                ))}
              </CardGrid>
            ) : (
              <EmptyState title={copy.empty.works} illustration="skins" />
            ),
          },
          {
            value: "collections",
            label: copy.tabs.collections,
            content: works.collections.length ? (
              <CardGrid>
                {works.collections.map((collection) => (
                  <CollectionCard key={collection.id} collection={collection} />
                ))}
              </CardGrid>
            ) : (
              <EmptyState title={copy.empty.collections} illustration="packs" />
            ),
          },
          {
            value: "setup",
            label: copy.tabs.setup,
            content: <EmptyState title={copy.empty.setup} illustration="mods" />,
          },
        ]}
      />
    </Container>
  );
}
