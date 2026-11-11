import { Container } from "@/components/layout/Container";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Tabs } from "@/components/ui/Tabs";
import { CollectionCard } from "@/features/library/CollectionCard";
import { ActivityRow } from "@/features/activity/ActivityRow";

import { type PublicProfile, getProfileWorks } from "./api";
import { ProfileSkin } from "./ProfileSkin";

const copy = {
  since: (date: string) =>
    `З нами з ${new Date(date).toLocaleDateString("uk-UA", { month: "long", year: "numeric" })}`,
  private: "Закритий профіль",
  privateText: "Гравець вирішив не показувати свій профіль.",
  tabsLabel: "Розділи профілю",
  tabs: { shared: "Поділився", collections: "Добірки" },
  empty: {
    shared: "Гравець ще нічим не поділився.",
    collections: "Публічних добірок поки немає.",
  },
};

export async function ProfileView({ profile }: { profile: PublicProfile }) {
  // A closed profile seen by someone else comes with everything but the nickname null
  if (profile.is_private && profile.date_joined === null) {
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
  const shared = works.shared?.results ?? [];

  return (
    <Container className="flex flex-col gap-16 py-12 md:py-16">
      <header className="flex flex-col gap-10 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:gap-10">
          <Avatar name={profile.nickname} src={profile.avatar_url} size={128} />
          <div className="flex flex-col gap-3">
            <h1 className="text-h1">{profile.nickname}</h1>
            <div className="flex flex-wrap items-center gap-3">
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
            value: "shared",
            label: shared.length
              ? `${copy.tabs.shared} · ${works.shared?.count}`
              : copy.tabs.shared,
            content: shared.length ? (
              <ul className="flex max-w-3xl flex-col border-t border-line">
                {shared.map((item) => (
                  <ActivityRow key={`${item.type}-${item.kind}-${item.id}`} item={item} />
                ))}
              </ul>
            ) : (
              <EmptyState title={copy.empty.shared} illustration="packs" />
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
        ]}
      />
    </Container>
  );
}
