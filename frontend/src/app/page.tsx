import { Suspense } from "react";

import { HealthStatus } from "@/features/health/HealthStatus";

const copy = {
  title: "BlockCraft Ukraine",
  checking: "Перевіряємо сервіси…",
};

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col justify-center gap-8 px-4 py-16 md:px-8">
      <h1 className="text-5xl font-medium">{copy.title}</h1>
      <Suspense fallback={<p>{copy.checking}</p>}>
        <HealthStatus />
      </Suspense>
    </main>
  );
}
