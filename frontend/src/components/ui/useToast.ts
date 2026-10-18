"use client";

import { useContext } from "react";

import { ToastContext } from "./ToastProvider";

/** Returns `toast({ title, description, tone })`. Needs <ToastProvider> above. */
export function useToast() {
  const toast = useContext(ToastContext);
  if (!toast) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return toast;
}
