"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { FormError } from "@/features/auth/FormError";
import { safeNext } from "@/features/auth/next-url";
import { type Me, useMe } from "@/features/auth/useMe";
import { GameProfileFields, type GameProfileValues } from "@/features/game/GameProfileFields";
import { api } from "@/lib/api/client";
import { fieldErrors } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

const copy = {
  done: "Готово",
  skip: "Пропустити",
  error: "Не вдалося зберегти. Спробуй ще раз.",
};

/** /welcome: what the player plays — sets catalog defaults. Can be skipped. */
export function OnboardingForm() {
  const { me, isLoading } = useMe();
  if (isLoading || !me) return <Skeleton className="h-96 w-full" />;
  return <OnboardingFields me={me} />;
}

function OnboardingFields({ me }: { me: Me }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const next = safeNext(useSearchParams().get("next"));
  const profile = me.game_profile;
  const [values, setValues] = useState<GameProfileValues>({
    game_version: profile.game_version ?? "",
    loader: profile.loader ?? "",
    edition: profile.edition ?? "java",
    interests: profile.interests ?? [],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<"save" | "skip" | null>(null);

  async function submit(skip: boolean) {
    setBusy(skip ? "skip" : "save");
    setErrors({});
    const body = skip
      ? {}
      : { ...values, loader: values.edition === "java" ? values.loader : ("" as const) };
    const { error, response } = await api.POST("/api/v1/me/onboarding", { body });
    setBusy(null);
    if (!response.ok) {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { root: copy.error });
      return;
    }
    await queryClient.invalidateQueries({ queryKey: queryKeys.me.all });
    router.replace(next);
  }

  return (
    <form
      noValidate
      className="flex flex-col gap-10"
      onSubmit={(event) => {
        event.preventDefault();
        void submit(false);
      }}
    >
      <FormError message={errors.root} />
      <GameProfileFields values={values} onChange={setValues} errors={errors} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg" loading={busy === "save"} disabled={busy !== null}>
          {copy.done}
        </Button>
        <Button
          variant="ghost"
          size="lg"
          loading={busy === "skip"}
          disabled={busy !== null}
          onClick={() => void submit(true)}
        >
          {copy.skip}
        </Button>
      </div>
    </form>
  );
}
