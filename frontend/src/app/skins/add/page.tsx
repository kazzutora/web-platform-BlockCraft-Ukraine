import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { AddSkin } from "@/features/skins/AddSkin";
import { skinsCopy } from "@/features/skins/copy";

export const metadata: Metadata = { title: skinsCopy.add.title, robots: { index: false } };

export default function AddSkinPage({ searchParams }: PageProps<"/skins/add">) {
  return (
    <FormPage title={skinsCopy.add.title} description={skinsCopy.add.lead}>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <Form searchParams={searchParams} />
      </Suspense>
    </FormPage>
  );
}

async function Form({ searchParams }: Pick<PageProps<"/skins/add">, "searchParams">) {
  const nickname = (await searchParams).nickname;
  return <AddSkin initialNickname={typeof nickname === "string" ? nickname.slice(0, 16) : ""} />;
}
