import { DetailPage } from "@/components/layout/DetailPage";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { Icon } from "@/components/ui/Icon";
import { Illustration } from "@/components/ui/Illustration";
import { SaveButton } from "@/components/ui/SaveButton";
import { StarRating } from "@/components/ui/StarRating";

export default function DetailTemplatePage() {
  return (
    <DetailPage
      media={
        <div className="flex size-full items-center justify-center">
          <Illustration name="mods" size={240} />
        </div>
      }
      eyebrow={<Chip tone="mods">Мод</Chip>}
      title="Sodium"
      description="Сучасний рушій рендерингу: значно більше кадрів на секунду без зміни вигляду гри."
      meta={<StarRating value={4.8} count={1204} />}
      primaryAction={
        <Button size="lg">
          <Icon name="download" /> Завантажити для 1.21 · Fabric
        </Button>
      }
      secondaryActions={
        <>
          <SaveButton count={3421} />
          <Button variant="secondary" size="lg">
            <Icon name="plus" /> В колекцію
          </Button>
        </>
      }
      tabsLabel="Сторінка мода"
      tabs={[
        {
          value: "about",
          label: "Опис",
          content: (
            <p className="max-w-prose">
              Sodium замінює систему рендерингу Minecraft і помітно підвищує продуктивність.
            </p>
          ),
        },
        { value: "versions", label: "Версії", content: <p>Версії з’являться на етапі 3.</p> },
        { value: "reviews", label: "Відгуки", content: <p>Відгуки — етап 4.</p> },
        { value: "similar", label: "Схоже", content: <p>Схожі проєкти.</p> },
      ]}
    />
  );
}
