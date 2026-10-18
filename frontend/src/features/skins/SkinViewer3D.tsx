"use client";

import { useEffect, useRef } from "react";
import {
  IdleAnimation,
  RunningAnimation,
  SkinViewer,
  WalkingAnimation,
  WaveAnimation,
} from "skinview3d";

import type { SkinModel } from "./types";

export type Pose = "walk" | "run" | "idle" | "wave";

const animations = {
  walk: () => new WalkingAnimation(),
  run: () => new RunningAnimation(),
  idle: () => new IdleAnimation(),
  wave: () => new WaveAnimation(),
} satisfies Record<Pose, () => unknown>;

export type SkinViewer3DProps = {
  texture: string;
  model: SkinModel;
  pose: Pose;
  label: string;
  /** Called once the texture is on the model (the fallback image can go). */
  onReady?: () => void;
};

/** skinview3d canvas: slow rotation and an animated pose; a still frame for reduced motion. */
export default function SkinViewer3D({ texture, model, pose, label, onReady }: SkinViewer3DProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewerRef = useRef<SkinViewer | null>(null);
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  });

  useEffect(() => {
    const host = hostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas) return;
    const viewer = new SkinViewer({
      canvas,
      width: host.clientWidth,
      height: host.clientHeight,
      zoom: 0.8,
      fov: 45,
    });
    viewer.controls.enableZoom = false;
    viewer.controls.enablePan = false;
    viewerRef.current = viewer;
    const resize = new ResizeObserver(([entry]) => {
      viewer.setSize(entry.contentRect.width, entry.contentRect.height);
    });
    resize.observe(host);
    return () => {
      resize.disconnect();
      viewer.dispose();
      viewerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer
      .loadSkin(texture, { model: model === "slim" ? "slim" : "default" })
      .then(() => onReadyRef.current?.())
      .catch(() => {
        // Keep the fallback image: the texture did not load
      });
  }, [texture, model]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      viewer.animation = reduced.matches ? null : animations[pose]();
      viewer.autoRotate = !reduced.matches;
      viewer.autoRotateSpeed = 0.6;
    };
    apply();
    reduced.addEventListener("change", apply);
    return () => reduced.removeEventListener("change", apply);
  }, [pose]);

  return (
    <div ref={hostRef} className="size-full">
      <canvas ref={canvasRef} role="img" aria-label={label} className="size-full cursor-grab" />
    </div>
  );
}
