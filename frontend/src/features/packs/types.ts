import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type PackCard = Schemas["PackCard"];
export type MyPack = Schemas["MyPack"];
export type PackDetail = Schemas["PackDetail"];
export type PackItem = Schemas["PackItem"];
export type PackIcon = Schemas["PackIcon"];
export type Issue = Schemas["Issue"];
export type PackStyle = Schemas["PackStyleEnum"];
export type PackLoader = Schemas["PackLoaderEnum"];
export type PackWrite = Schemas["PackWriteRequest"];
export type CatalogQuery = NonNullable<operations["packs_list"]["parameters"]["query"]>;

export const packLoaders: PackLoader[] = ["fabric", "neoforge", "forge", "quilt"];
export const packStyles: PackStyle[] = [
  "performance",
  "vanilla-plus",
  "survival",
  "adventure",
  "tech",
  "magic",
  "building",
  "quests",
  "multiplayer",
  "lightweight",
];
export const MAX_STYLES = 3;
