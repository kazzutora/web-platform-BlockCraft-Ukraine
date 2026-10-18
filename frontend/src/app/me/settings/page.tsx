import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { settingsCopy } from "@/features/settings/copy";
import { SettingsTabs } from "@/features/settings/SettingsTabs";

export const metadata: Metadata = { title: settingsCopy.title };

export default function SettingsPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{settingsCopy.title}</h1>
      <SettingsTabs />
    </Container>
  );
}
