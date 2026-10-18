import type { ReactNode } from "react";

import { Container } from "./Container";

type FormPageProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

/** Narrow centered column for forms: sign-in, settings, uploads. */
export function FormPage({ title, description, children }: FormPageProps) {
  return (
    <Container className="py-12 md:py-16">
      <div className="mx-auto flex max-w-xl flex-col gap-10">
        <header className="flex flex-col gap-3">
          <h1 className="text-h1">{title}</h1>
          {description && <p className="text-muted">{description}</p>}
        </header>
        {children}
      </div>
    </Container>
  );
}
