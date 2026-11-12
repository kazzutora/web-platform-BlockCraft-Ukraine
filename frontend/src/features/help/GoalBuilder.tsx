"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { useToast } from "@/components/ui/useToast";
import { ResolutionView } from "@/features/compat/ResolutionView";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

import { type GoalId, helpCopy } from "./copy";

type Preview = components["schemas"]["GoalsPreview"];

const copy = helpCopy.goal;
const GOALS = Object.keys(copy.goals) as GoalId[];

type GoalBuilderProps = {
  initialGoals: GoalId[];
  /** «1.21.1 · Fabric»; empty while «Моя гра» is not chosen. */
  gameLabel: string;
  /** «Моя гра» has a mod loader: goals are made of mods. */
  hasModLoader: boolean;
  signedIn: boolean;
};

/** /help/goal: pick goals, see the real mods that fit «Моя гра», save them as a pack. */
export function GoalBuilder({ initialGoals, gameLabel, hasModLoader, signedIn }: GoalBuilderProps) {
  const router = useRouter();
  const toast = useToast();
  const [goals, setGoals] = useState<GoalId[]>(initialGoals);

  const preview = useMutation({
    mutationFn: async (chosen: GoalId[]): Promise<Preview> => {
      const { data, error } = await api.POST("/api/v1/help/goals/preview", {
        body: { goals: chosen },
      });
      if (!data) throw error;
      return data;
    },
  });

  const save = useMutation({
    mutationFn: async (chosen: GoalId[]) => {
      const { data, error } = await api.POST("/api/v1/help/goals/pack", {
        body: { goals: chosen },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: (data) => {
      toast({ title: copy.saved });
      router.push(`/packs/${data.slug}/edit`);
    },
    onError: (error) => toast({ title: generalError(error, copy.saveError), tone: "danger" }),
  });

  function toggle(goal: GoalId) {
    preview.reset();
    setGoals((current) =>
      current.includes(goal) ? current.filter((item) => item !== goal) : [...current, goal],
    );
  }

  const ready = Boolean(gameLabel) && hasModLoader;
  // Goals in the address (a link from /help, the way back from signing in): pick at once
  const started = useRef(false);
  const { mutate: pick } = preview;
  useEffect(() => {
    if (started.current || !ready || !initialGoals.length) return;
    started.current = true;
    pick(initialGoals);
  }, [ready, initialGoals, pick]);
  const result = preview.data;
  const titles = new Map(
    result?.resolution.items.map((item) => [item.project.slug, item.project.title]),
  );
  const next = `/help/goal?goals=${goals.join(",")}`;

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-4">
        <FilterRow label={copy.goalsLabel}>
          {GOALS.map((goal) => (
            <FilterChip key={goal} active={goals.includes(goal)} onClick={() => toggle(goal)}>
              {copy.goals[goal].title}
            </FilterChip>
          ))}
        </FilterRow>
        <ul className="grid gap-x-8 gap-y-2 text-sm text-muted sm:grid-cols-2">
          {GOALS.filter((goal) => goals.includes(goal)).map((goal) => (
            <li key={goal}>
              <span className="text-text">{copy.goals[goal].title}</span> — {copy.goals[goal].text}
            </li>
          ))}
        </ul>
        <p className="text-sm">
          {!gameLabel ? copy.noGame : hasModLoader ? copy.game(gameLabel) : copy.needsLoader}
        </p>
        <Button
          size="lg"
          variant={result ? "secondary" : "primary"}
          className="self-start"
          disabled={!ready || !goals.length}
          loading={preview.isPending}
          onClick={() => preview.mutate(goals)}
        >
          {preview.isPending ? copy.picking : copy.pick}
        </Button>
        {preview.isError && (
          <p className="text-danger">{generalError(preview.error, copy.error)}</p>
        )}
      </div>

      {result && (
        <section aria-live="polite" className="flex flex-col gap-8">
          <div className="flex flex-col gap-4">
            <h2 className="text-h2">{copy.chosen}</h2>
            <ul className="flex flex-col border-t border-line">
              {result.choices.map((choice) => {
                const slot = copy.slots[choice.slot] ?? choice.slot;
                return (
                  <li
                    key={choice.slot}
                    className="flex flex-wrap justify-between gap-2 border-b border-line py-3"
                  >
                    <span className="text-muted">{slot}</span>
                    {choice.slug ? (
                      <span className="font-medium">{titles.get(choice.slug) ?? choice.slug}</span>
                    ) : (
                      <span className="text-sm text-muted">{copy.nothing(slot)}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
          {signedIn ? (
            <Button
              size="lg"
              className="self-start"
              loading={save.isPending}
              disabled={!result.choices.some((choice) => choice.slug)}
              onClick={() => save.mutate(goals)}
            >
              {save.isPending ? copy.saving : copy.save}
            </Button>
          ) : (
            <ButtonLink
              href={`/login?next=${encodeURIComponent(next)}`}
              size="lg"
              className="self-start"
            >
              {copy.signIn}
            </ButtonLink>
          )}
          <ResolutionView resolution={result.resolution} title={copy.resolution} live={false} />
        </section>
      )}
    </div>
  );
}
