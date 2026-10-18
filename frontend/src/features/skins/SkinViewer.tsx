"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useState } from "react";

import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { cn } from "@/lib/cn";

import { skinsCopy } from "./copy";
import type { Pose } from "./SkinViewer3D";
import type { SkinModel } from "./types";

const copy = skinsCopy.poses;

// three.js stays out of the server bundle and loads only where a skin is shown
const SkinViewer3D = dynamic(() => import("./SkinViewer3D"), { ssr: false });

const poseOptions: { value: Pose; label: string }[] = [
  { value: "walk", label: copy.walk },
  { value: "run", label: copy.run },
  { value: "idle", label: copy.idle },
  { value: "wave", label: copy.wave },
];

type SkinViewerProps = {
  texture: string;
  model: SkinModel;
  title: string;
  /** 2D image shown until the 3D model is ready (and if WebGL is unavailable). */
  fallback?: string | null;
  /** Show the pose switch under the model. */
  poses?: boolean;
};

export function SkinViewer({ texture, model, title, fallback, poses = true }: SkinViewerProps) {
  const [pose, setPose] = useState<Pose>("walk");
  const [ready, setReady] = useState(false);

  return (
    <div className="flex size-full flex-col">
      <div className="relative min-h-0 flex-1">
        {fallback && (
          <Image
            src={fallback}
            alt=""
            width={128}
            height={256}
            unoptimized
            className={cn(
              "absolute inset-0 m-auto h-3/4 w-auto object-contain transition-opacity duration-300 [image-rendering:pixelated]",
              ready && "opacity-0",
            )}
          />
        )}
        <div className="absolute inset-0">
          <SkinViewer3D
            texture={texture}
            model={model}
            pose={pose}
            label={skinsCopy.viewer.label(title)}
            onReady={() => setReady(true)}
          />
        </div>
      </div>
      {poses && (
        <div className="border-t border-line p-3">
          <ChoiceChips
            label={copy.label}
            hideLabel
            options={poseOptions}
            value={pose}
            onChange={setPose}
          />
        </div>
      )}
    </div>
  );
}
