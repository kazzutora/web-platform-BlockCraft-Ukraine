"use client";

import { useEffect, useRef } from "react";

import { takePendingAction } from "./pending-action";
import { useMe } from "./useMe";

/** Replays an action a guest started before signing in (requireAuth with `pendingKey`). */
export function usePendingAction(key: string, run: () => void): void {
  const { me } = useMe();
  const runRef = useRef(run);
  useEffect(() => {
    runRef.current = run;
  });

  useEffect(() => {
    if (!me) return;
    const here = `${window.location.pathname}${window.location.search}`;
    if (takePendingAction(key, here)) runRef.current();
  }, [me, key]);
}
