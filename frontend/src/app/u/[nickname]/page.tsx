import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getPublicProfile } from "@/features/profile/api";
import { ProfileView } from "@/features/profile/ProfileView";

export async function generateMetadata({ params }: PageProps<"/u/[nickname]">): Promise<Metadata> {
  const { nickname } = await params;
  return { title: decodeURIComponent(nickname) };
}

export default function ProfilePage({ params }: PageProps<"/u/[nickname]">) {
  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <Profile params={params} />
    </Suspense>
  );
}

async function Profile({ params }: Pick<PageProps<"/u/[nickname]">, "params">) {
  const { nickname } = await params;
  const profile = await getPublicProfile(decodeURIComponent(nickname));
  if (!profile) notFound();
  return <ProfileView profile={profile} />;
}

function ProfileSkeleton() {
  return (
    <Container className="flex flex-col gap-6 py-12 md:flex-row md:items-center md:gap-10 md:py-16">
      <Skeleton className="size-32" />
      <div className="flex flex-col gap-3">
        <Skeleton className="h-14 w-64" />
        <Skeleton className="h-6 w-40" />
      </div>
    </Container>
  );
}
