import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type SearchHit = Schemas["SearchHit"];
export type SearchGroup = Schemas["SearchGroup"];
export type SearchKind = NonNullable<
  NonNullable<operations["search"]["parameters"]["query"]>["kind"]
>;

export const searchKinds: SearchKind[] = ["mod", "skin", "server", "collection"];
