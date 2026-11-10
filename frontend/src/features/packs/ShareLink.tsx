"use client";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";

import { packsCopy } from "./copy";

const copy = packsCopy.detail;

/** «За посиланням»: the address with the token, for the author to send to friends. */
export function ShareLink({ slug, token }: { slug: string; token: string }) {
  const toast = useToast();
  const path = `/packs/${slug}?share_token=${encodeURIComponent(token)}`;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(new URL(path, window.location.origin).toString());
      toast({ title: copy.copied });
    } catch {
      toast({ title: copy.error, tone: "danger" });
    }
  }

  return (
    <div className="flex flex-col gap-2 border border-line p-4 sm:flex-row sm:items-center">
      <span className="text-meta text-muted">{copy.share}</span>
      <code className="min-w-0 flex-1 truncate font-mono text-sm">{path}</code>
      <Button variant="secondary" onClick={() => void copyLink()}>
        <Icon name="copy" />
        {copy.copyLink}
      </Button>
    </div>
  );
}
