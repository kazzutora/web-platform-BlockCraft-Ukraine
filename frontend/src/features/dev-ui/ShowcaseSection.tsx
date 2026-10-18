import type { ReactNode } from "react";

/** One block of the /dev/ui showcase. */
export function ShowcaseSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="flex flex-col gap-6 border-t border-line pt-10"
    >
      <h2 id={`${id}-title`} className="text-h2">
        {title}
      </h2>
      {children}
    </section>
  );
}
