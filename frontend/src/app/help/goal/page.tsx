import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Suspense } from "react";

import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/Skeleton";
import { getGameContext } from "@/features/game/context";
import { gameName } from "@/features/game/labels";
import { type GoalId, helpCopy } from "@/features/help/copy";
import { GoalBuilder } from "@/features/help/GoalBuilder";
import { looksSignedIn } from "@/lib/session";

const copy = helpCopy.goal;
const GOALS = new Set(Object.keys(copy.goals));
const MOD_LOADERS = new Set(["fabric", "quilt", "forge", "neoforge"]);

export const metadata: Metadata = { title: copy.title, description: copy.description };

export default function GoalPage({ searchParams }: PageProps<"/help/goal">) {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <header className="flex max-w-prose flex-col gap-4">
        <h1 className="text-h1">{copy.title}</h1>
        <p className="text-lg text-muted">{copy.description}</p>
      </header>
      <Suspense fallback={<Skeleton className="h-48 w-full" />}>
        <Builder searchParams={searchParams} />
      </Suspense>
    </Container>
  );
}

async function Builder({ searchParams }: Pick<PageProps<"/help/goal">, "searchParams">) {
  const [params, game, jar] = await Promise.all([searchParams, getGameContext(), cookies()]);
  const raw = Array.isArray(params.goals) ? params.goals.join(",") : (params.goals ?? "");
  const goals = raw.split(",").filter((goal): goal is GoalId => GOALS.has(goal));
  return (
    <GoalBuilder
      initialGoals={goals}
      gameLabel={game.source === "none" ? "" : gameName(game)}
      hasModLoader={MOD_LOADERS.has(game.loader)}
      signedIn={looksSignedIn(jar)}
    />
  );
}
