import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type ServerCard = Schemas["ServerCard"];
export type ServerDetail = Schemas["ServerDetail"];
export type LiveStatus = Schemas["LiveStatus"];
export type Stats = Schemas["Stats"];
export type StatsPoint = Schemas["StatsPoint"];
export type Join = Schemas["Join"];
export type ContentKind = Schemas["ServerContentKindEnum"];
export type ServerEdition = Schemas["EditionEnum"];
export type ServerCategory = Schemas["ServerCategory"];
export type VerificationState = Schemas["StateEnum"];
export type ServerWrite = Schemas["PatchedServerWriteRequest"];
export type CatalogQuery = NonNullable<operations["servers_list"]["parameters"]["query"]>;
export type StatsRange = "24h" | "7d";

export const contentKinds: ContentKind[] = ["vanilla", "modded"];
