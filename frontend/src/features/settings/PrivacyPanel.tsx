"use client";

import { useState } from "react";

import { Checkbox } from "@/components/ui/Checkbox";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { useToast } from "@/components/ui/useToast";
import type { Me } from "@/features/auth/useMe";

import { settingsCopy } from "./copy";
import { type UserSettings, useUpdateAccount, useUpdateSettings } from "./useSettings";

const copy = settingsCopy.privacy;

type Values = {
  is_private: boolean;
  who_can_comment: NonNullable<UserSettings["who_can_comment"]>;
  collections_visible: boolean;
  history_enabled: boolean;
};

/** Every switch saves immediately: optimistic, rolled back with a toast on error. */
export function PrivacyPanel({ me, settings }: { me: Me; settings: UserSettings }) {
  const toast = useToast();
  const updateAccount = useUpdateAccount();
  const updateSettings = useUpdateSettings();
  const [values, setValues] = useState<Values>({
    is_private: me.is_private,
    who_can_comment: settings.who_can_comment ?? "all",
    collections_visible: settings.collections_visible ?? true,
    history_enabled: settings.history_enabled ?? true,
  });

  function change<K extends keyof Values>(key: K, value: Values[K]) {
    const previous = values[key];
    setValues((current) => ({ ...current, [key]: value }));
    const options = {
      onSuccess: () => toast({ title: settingsCopy.saved }),
      onError: () => {
        setValues((current) => ({ ...current, [key]: previous }));
        toast({ title: settingsCopy.error, tone: "danger" });
      },
    };
    if (key === "is_private") {
      updateAccount.mutate({ is_private: value as boolean }, options);
    } else {
      updateSettings.mutate({ [key]: value }, options);
    }
  }

  return (
    <div className="flex max-w-xl flex-col gap-8">
      <Checkbox
        label={copy.isPrivate}
        hint={copy.isPrivateHint}
        checked={values.is_private}
        onChange={(event) => change("is_private", event.target.checked)}
      />
      <ChoiceChips
        label={copy.whoCanComment}
        options={copy.commentPolicies}
        value={values.who_can_comment}
        onChange={(value) => change("who_can_comment", value)}
      />
      <Checkbox
        label={copy.collectionsVisible}
        checked={values.collections_visible}
        onChange={(event) => change("collections_visible", event.target.checked)}
      />
      <Checkbox
        label={copy.historyEnabled}
        checked={values.history_enabled}
        onChange={(event) => change("history_enabled", event.target.checked)}
      />
    </div>
  );
}
