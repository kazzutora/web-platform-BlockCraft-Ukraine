"use client";

import { useContext } from "react";

import { AuthPromptContext } from "./AuthPromptProvider";

/** See AuthPromptProvider. */
export function useRequireAuth() {
  const requireAuth = useContext(AuthPromptContext);
  if (!requireAuth) {
    throw new Error("useRequireAuth must be used inside <AuthPromptProvider>");
  }
  return requireAuth;
}
