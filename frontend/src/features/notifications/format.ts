import { hitHref } from "@/features/search/hits";

import { notificationsCopy as copy } from "./copy";
import type { Notification } from "./types";

/** The line of text and, if the object is known, where the notification leads. */
export function describe(notification: Notification): { text: string; href: string | null } {
  const payload = { ...notification.payload, actor: notification.payload.actor ?? copy.someone };
  const { kind, id } = notification.payload;
  return {
    text: copy.texts[notification.type](payload),
    href: kind && id ? hitHref({ kind, id }) : null,
  };
}
