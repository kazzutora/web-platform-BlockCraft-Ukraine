import type { ChoiceOption } from "@/components/ui/ChoiceChips";
import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
/** A supported version from GET /meta (synced from Modrinth). */
export type GameVersion = string;
export type Loader = Schemas["LoaderEnum"];
export type Edition = Schemas["EditionEnum"];

/** Ukrainian labels for the game vocabulary (values come from the API schema). */
export const loaderOptions: ChoiceOption<Loader>[] = [
  { value: "fabric", label: "Fabric" },
  { value: "forge", label: "Forge" },
  { value: "neoforge", label: "NeoForge" },
  { value: "quilt", label: "Quilt" },
  { value: "vanilla", label: "Без модів" },
];

export const editionOptions: ChoiceOption<Edition>[] = [
  { value: "java", label: "Java" },
  { value: "bedrock", label: "Bedrock" },
];

/** «1.21.1 · Fabric», «1.21.1 · Без модів»: «Моя гра» in a sentence (server and client). */
export function gameName({ game_version, loader }: { game_version: string; loader: string }) {
  const label = loaderOptions.find((option) => option.value === loader)?.label ?? "";
  return [game_version, label].filter(Boolean).join(" · ");
}
