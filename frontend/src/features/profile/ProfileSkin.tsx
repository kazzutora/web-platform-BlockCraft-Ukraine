"use client";

import { skinsCopy } from "@/features/skins/copy";
import { SkinViewer } from "@/features/skins/SkinViewer";
import { usePlayerSkin } from "@/features/skins/usePlayerSkin";

import type { PublicProfile } from "./api";

type ProfileSkinProps = {
  nickname: string;
  skin: PublicProfile["skin"];
  /** Fallback: the skin of the player's Minecraft account. */
  mcNickname: string | null;
};

/** The chosen skin in 3D, else the Mojang skin of `mc_nickname`, else nothing. */
export function ProfileSkin({ nickname, skin, mcNickname }: ProfileSkinProps) {
  const mojang = usePlayerSkin(skin ? "" : (mcNickname ?? ""));
  const texture = skin?.texture_url ?? mojang.data?.texture ?? null;
  const model = skin?.model ?? mojang.data?.model ?? null;
  if (!texture || (model !== "classic" && model !== "slim")) return null;

  return (
    <div className="aspect-square w-full max-w-64 border border-line bg-surface">
      <SkinViewer
        texture={texture}
        model={model}
        title={skinsCopy.profile.skin(nickname)}
        poses={false}
      />
    </div>
  );
}
