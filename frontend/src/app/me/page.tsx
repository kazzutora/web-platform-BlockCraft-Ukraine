import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { activityCopy } from "@/features/activity/copy";
import { MeDashboard } from "@/features/activity/MeDashboard";

export const metadata: Metadata = { title: activityCopy.me.title, robots: { index: false } };

export default function MePage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{activityCopy.me.title}</h1>
      <MeDashboard />
    </Container>
  );
}
