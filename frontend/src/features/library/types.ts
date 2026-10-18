import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type Kind = Schemas["KindEnum"];
export type Collection = Schemas["Collection"];
export type CollectionDetail = Schemas["CollectionDetail"];
export type CollectionItem = Schemas["CollectionItem"];
export type MyCollection = Schemas["MyCollection"];
export type SavedItem = Schemas["SavedItem"];
export type Visibility = Schemas["VisibilityEnum"];
