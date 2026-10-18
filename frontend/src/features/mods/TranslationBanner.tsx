"use client";

import { Icon } from "@/components/ui/Icon";
import { useMe } from "@/features/auth/useMe";

import { modsCopy } from "./copy";

const copy = modsCopy.detail;

/** For moderators only: the Ukrainian summary is missing, edit it in the admin. */
export function TranslationBanner({ projectId }: { projectId: number }) {
  const { me } = useMe();
  if (!me || (me.role !== "moderator" && me.role !== "admin")) return null;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border border-text p-4 text-sm">
      <p className="flex items-center gap-2">
        <Icon name="pencil" />
        {copy.translationBanner}
      </p>
      <a
        href={`/admin/mods/project/${projectId}/change/`}
        className="font-medium underline underline-offset-4"
      >
        {copy.translationAction}
      </a>
    </div>
  );
}
