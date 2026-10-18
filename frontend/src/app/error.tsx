"use client";

import { useEffect } from "react";

import { Container } from "@/components/layout/Container";
import { Button } from "@/components/ui/Button";
import { Illustration } from "@/components/ui/Illustration";

const copy = {
  title: "Щось пішло не так",
  text: "Ми вже знаємо про помилку. Спробуй ще раз за мить.",
  retry: "Спробувати ще",
};

export default function ErrorPage({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Container className="flex flex-1 flex-col items-center justify-center gap-8 py-24 text-center">
      <Illustration name="error" size={160} />
      <h1 className="text-h1">{copy.title}</h1>
      <p className="max-w-prose text-muted">{copy.text}</p>
      <Button size="lg" onClick={() => retry()}>
        {copy.retry}
      </Button>
    </Container>
  );
}
