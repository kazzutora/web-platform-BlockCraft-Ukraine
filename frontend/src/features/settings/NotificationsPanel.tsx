"use client";

import { useState } from "react";

import { Checkbox } from "@/components/ui/Checkbox";
import { useToast } from "@/components/ui/useToast";
import { notificationsCopy } from "@/features/notifications/copy";

import { settingsCopy } from "./copy";
import { type UserSettings, useUpdateSettings } from "./useSettings";

const copy = notificationsCopy.prefs;
const OPTIONAL = ["reply", "review"] as const;
type Optional = (typeof OPTIONAL)[number];
type Prefs = Record<string, boolean>;

/** Which notifications to receive; moderation decisions always arrive. Saves at once. */
export function NotificationsPanel({ settings }: { settings: UserSettings }) {
  const toast = useToast();
  const update = useUpdateSettings();
  const [prefs, setPrefs] = useState<Prefs>((settings.notify_prefs as Prefs | undefined) ?? {});

  function change(type: Optional, enabled: boolean) {
    const previous = prefs;
    const next = { ...prefs, [type]: enabled };
    setPrefs(next);
    update.mutate(
      { notify_prefs: next },
      {
        onSuccess: () => toast({ title: settingsCopy.saved }),
        onError: () => {
          setPrefs(previous);
          toast({ title: settingsCopy.error, tone: "danger" });
        },
      },
    );
  }

  return (
    <fieldset className="flex max-w-xl flex-col gap-6">
      <legend className="mb-2 text-sm font-medium">{copy.title}</legend>
      {OPTIONAL.map((type) => (
        <Checkbox
          key={type}
          label={copy[type]}
          checked={prefs[type] !== false}
          onChange={(event) => change(type, event.target.checked)}
        />
      ))}
      <p className="text-meta text-muted">{copy.hint}</p>
    </fieldset>
  );
}
