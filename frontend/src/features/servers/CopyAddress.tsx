"use client";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";

import { serversCopy } from "./copy";

type CopyAddressProps = {
  slug: string;
  address: string;
  size?: "md" | "lg";
  variant?: "primary" | "secondary";
};

/** «Скопіювати IP»: copies the address and counts it (no sign-in needed). */
export function CopyAddress({
  slug,
  address,
  size = "md",
  variant = "secondary",
}: CopyAddressProps) {
  const toast = useToast();

  async function copyAddress() {
    try {
      await navigator.clipboard.writeText(address);
    } catch {
      toast({ title: serversCopy.copyFailed, tone: "danger" });
      return;
    }
    toast({ title: serversCopy.copied(address) });
    // The counter is best effort: a failed request must not bother the player
    void api.POST("/api/v1/servers/{slug}/copy-ip", { params: { path: { slug } } }).catch(() => {});
  }

  return (
    <Button variant={variant} size={size} onClick={copyAddress}>
      <Icon name="copy" />
      {serversCopy.copyIp}
    </Button>
  );
}
