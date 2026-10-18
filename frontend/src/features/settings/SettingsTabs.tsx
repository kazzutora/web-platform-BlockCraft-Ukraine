"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useMe } from "@/features/auth/useMe";

import { AppearancePanel } from "./AppearancePanel";
import { settingsCopy } from "./copy";
import { GamePanel } from "./GamePanel";
import { PrivacyPanel } from "./PrivacyPanel";
import { ProfilePanel } from "./ProfilePanel";
import { SecurityPanel } from "./SecurityPanel";
import { useSettings } from "./useSettings";

const copy = settingsCopy.tabs;

export function SettingsTabs() {
  const { me } = useMe();
  const { data: settings } = useSettings();

  if (!me || !settings) return <Skeleton className="h-96 w-full" />;

  return (
    <Tabs
      label={copy.label}
      items={[
        { value: "profile", label: copy.profile, content: <ProfilePanel me={me} /> },
        { value: "game", label: copy.game, content: <GamePanel me={me} /> },
        {
          value: "appearance",
          label: copy.appearance,
          content: <AppearancePanel settings={settings} />,
        },
        {
          value: "privacy",
          label: copy.privacy,
          content: <PrivacyPanel me={me} settings={settings} />,
        },
        { value: "security", label: copy.security, content: <SecurityPanel me={me} /> },
      ]}
    />
  );
}
