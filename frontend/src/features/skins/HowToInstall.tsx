import { skinsCopy } from "./copy";
import type { SkinModel } from "./types";

const copy = skinsCopy.install;

/** «Як поставити»: short steps for Java and Bedrock side by side. */
export function HowToInstall({ model }: { model: SkinModel }) {
  const sections = [
    { title: copy.javaTitle, steps: copy.java },
    { title: copy.bedrockTitle, steps: copy.bedrock },
  ];
  return (
    <div className="flex flex-col gap-6">
      <p className="text-muted">
        {skinsCopy.form.model}: {skinsCopy.models[model]}
      </p>
      <div className="grid gap-6 md:grid-cols-2">
        {sections.map((section) => (
          <section key={section.title} className="flex flex-col gap-4 border border-line p-6">
            <h3 className="caps font-sans">{section.title}</h3>
            <ol className="flex list-decimal flex-col gap-2 pl-5">
              {section.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </div>
  );
}
