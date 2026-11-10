import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type PackCard = Schemas["PackCard"];
export type MyPack = Schemas["MyPack"];
export type PackDetail = Schemas["PackDetail"];
export type PackItem = Schemas["PackItem"];
export type PackIcon = Schemas["PackIcon"];
export type PackLoader = Schemas["PackLoaderEnum"];
export type PackWrite = Schemas["PackWriteRequest"];
export type PackVisibility = Schemas["PackVisibilityEnum"];
export type PackFile = Schemas["PackFileLink"];
export type Retarget = Schemas["Retarget"];
export type CatalogQuery = NonNullable<operations["packs_list"]["parameters"]["query"]>;

export const packLoaders: PackLoader[] = ["fabric", "neoforge", "forge", "quilt"];
