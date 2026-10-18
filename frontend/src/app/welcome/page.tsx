import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/layout/FormPage";
import { Skeleton } from "@/components/ui/Skeleton";
import { OnboardingForm } from "@/features/onboarding/OnboardingForm";

const copy = {
  title: "Як ти граєш?",
  description: "Підберемо моди й сервери під твою версію. Змінити можна будь-коли в налаштуваннях.",
};

export const metadata: Metadata = { title: copy.title };

export default function WelcomePage() {
  return (
    <FormPage title={copy.title} description={copy.description}>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <OnboardingForm />
      </Suspense>
    </FormPage>
  );
}
