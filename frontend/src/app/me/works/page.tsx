import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { Tabs } from "@/components/ui/Tabs";
import { serversCopy } from "@/features/servers/copy";
import { MyServers } from "@/features/servers/MyServers";
import { skinsCopy } from "@/features/skins/copy";
import { MySkins } from "@/features/skins/MySkins";

const copy = { title: "Мої роботи", tabsLabel: "Типи робіт" };

export const metadata: Metadata = { title: copy.title };

export default function MyWorksPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{copy.title}</h1>
      <Tabs
        label={copy.tabsLabel}
        items={[
          { value: "skins", label: skinsCopy.title, content: <MySkins /> },
          { value: "servers", label: serversCopy.title, content: <MyServers /> },
        ]}
      />
    </Container>
  );
}
