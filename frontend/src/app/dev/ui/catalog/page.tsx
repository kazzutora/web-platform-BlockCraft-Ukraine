import { CatalogPage } from "@/components/layout/CatalogPage";
import { Card } from "@/components/ui/Card";
import { CardGrid } from "@/components/ui/CardGrid";
import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { Illustration } from "@/components/ui/Illustration";
import { LoadMore } from "@/components/ui/LoadMore";
import { SaveButton } from "@/components/ui/SaveButton";
import { plural } from "@/lib/plural";

const titles = [
  "Sodium",
  "Lithium",
  "Iris Shaders",
  "Fabric API",
  "Mod Menu",
  "JEI",
  "Xaero's Minimap",
  "AppleSkin",
  "Create",
  "Farmer's Delight",
  "Waystones",
  "Journeymap",
];

export default function CatalogTemplatePage() {
  return (
    <CatalogPage
      illustration="mods"
      title="Моди"
      count={plural(312, { one: "мод", few: "моди", many: "модів" })}
      filters={
        <FilterRow label="Фільтри">
          <FilterChip href="/dev/ui/catalog" active>
            1.21.4
          </FilterChip>
          <FilterChip href="/dev/ui/catalog" active>
            Fabric
          </FilterChip>
          <FilterChip href="/dev/ui/catalog" active={false}>
            Оптимізація
          </FilterChip>
          <FilterChip href="/dev/ui/catalog" active={false}>
            Інтерфейс
          </FilterChip>
          <FilterChip href="/dev/ui/catalog" active={false}>
            Світ
          </FilterChip>
          <FilterChip href="/dev/ui/catalog" active={false}>
            Показати все
          </FilterChip>
        </FilterRow>
      }
      footer={<LoadMore href="/dev/ui/catalog" />}
    >
      <CardGrid>
        {titles.map((title) => (
          <Card
            key={title}
            href="/dev/ui/detail"
            title={title}
            meta="1.21 · Fabric · ★ 4,7"
            cover={
              <div className="flex size-full items-center justify-center">
                <Illustration name="mods" size={96} />
              </div>
            }
            action={<SaveButton />}
          />
        ))}
      </CardGrid>
    </CatalogPage>
  );
}
