import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { Tabs } from "@/components/ui/Tabs";
import { packsCopy } from "@/features/packs/copy";
import { MyPacks } from "@/features/packs/MyPacks";
import { serversCopy } from "@/features/servers/copy";
import { MyServers } from "@/features/servers/MyServers";

const copy = { title: "Мої збірки", tabsLabel: "Що я поширюю" };

export const metadata: Metadata = { title: copy.title };

/** /me/packs: the player's packs and servers (the full «Моє» cabinet comes in R7.4). */
export default function MyPacksPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{copy.title}</h1>
      <Tabs
        label={copy.tabsLabel}
        items={[
          { value: "packs", label: packsCopy.title, content: <MyPacks /> },
          { value: "servers", label: serversCopy.title, content: <MyServers /> },
        ]}
      />
    </Container>
  );
}
