import type { ChoiceOption } from "@/components/ui/ChoiceChips";
import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
export type GameVersion = Schemas["GameVersionEnum"];
export type Loader = Schemas["LoaderEnum"];
export type Edition = Schemas["EditionEnum"];
export type Interest = Schemas["InterestsEnum"];

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

export const interestOptions: ChoiceOption<Interest>[] = [
  { value: "survival", label: "Виживання" },
  { value: "building", label: "Будівництво" },
  { value: "tech", label: "Техніка й редстоун" },
  { value: "pvp", label: "PvP" },
  { value: "rp", label: "Рольова гра" },
  { value: "adventure", label: "Пригоди" },
  { value: "minigames", label: "Мініігри" },
  { value: "modded", label: "Моди й зборки" },
];

/** Newest first; the list is bounded by the backend (apps/core/game.py). */
export const gameVersions: GameVersion[] = [
  "26.3", "26.2", "26.1.2", "26.1.1", "26.1",
  "1.21.11", "1.21.10", "1.21.9", "1.21.8", "1.21.7", "1.21.6", "1.21.5", "1.21.4",
  "1.21.3", "1.21.2", "1.21.1", "1.21",
  "1.20.6", "1.20.5", "1.20.4", "1.20.3", "1.20.2", "1.20.1", "1.20",
  "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
  "1.18.2", "1.18.1", "1.18", "1.17.1", "1.17",
  "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1", "1.16",
  "1.12.2", "1.8.9",
]; // prettier-ignore

export const gameVersionOptions = gameVersions.map((version) => ({
  value: version,
  label: version,
}));
