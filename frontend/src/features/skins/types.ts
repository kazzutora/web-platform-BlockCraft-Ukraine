import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type SkinCard = Schemas["SkinCard"];
export type SkinDetail = Schemas["SkinDetail"];
export type SkinModel = Schemas["ModelEnum"];
export type ColorBucket = Schemas["ColorBucketEnum"];
export type Style = Schemas["StyleTagsEnum"];
export type LookupResult = Schemas["LookupResult"];
export type CatalogQuery = NonNullable<operations["skins_list"]["parameters"]["query"]>;

export const colorBuckets: ColorBucket[] = [
  "red",
  "orange",
  "yellow",
  "green",
  "cyan",
  "blue",
  "purple",
  "pink",
  "brown",
  "black",
  "white",
  "gray",
];

export const styles: Style[] = [
  "casual",
  "ukrainian",
  "fantasy",
  "medieval",
  "scifi",
  "anime",
  "horror",
  "cute",
  "mob",
  "military",
  "sport",
];

export const MAX_STYLES = 3;
export const MAX_FILE_BYTES = 100 * 1024;
