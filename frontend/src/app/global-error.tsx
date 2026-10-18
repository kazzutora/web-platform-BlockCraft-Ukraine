"use client";

import { Button } from "@/components/ui/Button";
import { Illustration } from "@/components/ui/Illustration";
import { cn } from "@/lib/cn";
import "@/styles/globals.css";

import { sans, serif } from "./fonts";

const copy = {
  title: "500 — сервер не відповідає",
  text: "Сталася помилка на нашому боці. Спробуй оновити сторінку.",
  retry: "Спробувати ще",
};

/** Replaces the root layout when it fails, so it brings its own document, fonts and styles. */
export default function GlobalError({ retry }: { error: unknown; retry: () => void }) {
  return (
    <html lang="uk" className={cn(serif.variable, sans.variable, "h-full antialiased")}>
      <body className="flex min-h-full flex-col items-center justify-center gap-8 px-4 py-24 text-center">
        <title>{copy.title}</title>
        <Illustration name="error" size={160} />
        <h1 className="text-h1">{copy.title}</h1>
        <p className="max-w-prose text-muted">{copy.text}</p>
        <Button size="lg" onClick={() => retry()}>
          {copy.retry}
        </Button>
      </body>
    </html>
  );
}
