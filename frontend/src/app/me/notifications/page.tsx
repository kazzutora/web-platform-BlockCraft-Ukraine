import type { Metadata } from "next";

import { Container } from "@/components/layout/Container";
import { notificationsCopy } from "@/features/notifications/copy";
import { NotificationsList } from "@/features/notifications/NotificationsList";

export const metadata: Metadata = { title: notificationsCopy.title };

export default function NotificationsPage() {
  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <h1 className="text-h1">{notificationsCopy.title}</h1>
      <NotificationsList />
    </Container>
  );
}
