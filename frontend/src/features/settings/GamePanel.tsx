"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/useToast";
import { FormError } from "@/features/auth/FormError";
import type { Me } from "@/features/auth/useMe";
import { GameProfileFields, type GameProfileValues } from "@/features/game/GameProfileFields";
import { fieldErrors } from "@/lib/api/errors";

import { settingsCopy } from "./copy";
import { useUpdateGameProfile } from "./useSettings";

export function GamePanel({ me }: { me: Me }) {
  const toast = useToast();
  const update = useUpdateGameProfile();
  const profile = me.game_profile;
  const [values, setValues] = useState<GameProfileValues>({
    game_version: profile.game_version ?? "",
    loader: profile.loader ?? "",
    edition: profile.edition ?? "java",
    interests: profile.interests ?? [],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function onSave() {
    setErrors({});
    try {
      await update.mutateAsync(values);
      toast({ title: settingsCopy.saved });
    } catch (error) {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { root: settingsCopy.error });
    }
  }

  return (
    <form
      noValidate
      className="flex max-w-xl flex-col gap-8"
      onSubmit={(event) => {
        event.preventDefault();
        void onSave();
      }}
    >
      <FormError message={errors.root} />
      <GameProfileFields values={values} onChange={setValues} errors={errors} />
      <Button type="submit" className="self-start" loading={update.isPending}>
        {settingsCopy.save}
      </Button>
    </form>
  );
}
