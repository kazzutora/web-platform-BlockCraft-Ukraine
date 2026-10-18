"use client";

import { useTheme } from "next-themes";
import { useState } from "react";

import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/useToast";

import { settingsCopy } from "./copy";
import { type UserSettings, useUpdateSettings } from "./useSettings";

const copy = settingsCopy.appearance;

type Theme = NonNullable<UserSettings["theme"]>;

/** Theme applies at once in this browser and is stored in the account. */
export function AppearancePanel({ settings }: { settings: UserSettings }) {
  const toast = useToast();
  const { setTheme } = useTheme();
  const update = useUpdateSettings();
  const [theme, setLocalTheme] = useState<Theme>(settings.theme ?? "light");

  function change(next: Theme) {
    const previous = theme;
    setLocalTheme(next);
    setTheme(next);
    update.mutate(
      { theme: next },
      {
        onSuccess: () => toast({ title: settingsCopy.saved }),
        onError: () => {
          setLocalTheme(previous);
          setTheme(previous);
          toast({ title: settingsCopy.error, tone: "danger" });
        },
      },
    );
  }

  return (
    <div className="flex max-w-xl flex-col gap-8">
      <ChoiceChips label={copy.theme} options={copy.themes} value={theme} onChange={change} />
      <Select
        label={copy.language}
        hint={copy.languageHint}
        options={[{ value: "uk", label: "Українська" }]}
        value="uk"
        disabled
        onChange={() => undefined}
      />
    </div>
  );
}
