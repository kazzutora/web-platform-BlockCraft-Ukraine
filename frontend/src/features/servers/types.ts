import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type ServerCard = Schemas["ServerCard"];
export type ServerDetail = Schemas["ServerDetail"];
export type LiveStatus = Schemas["LiveStatus"];
export type Stats = Schemas["Stats"];
export type StatsPoint = Schemas["StatsPoint"];
export type Edition = Schemas["ServerEditionEnum"];
export type Language = Schemas["ServerLanguageEnum"];
export type Mode = Schemas["ModesEnum"];
export type VerificationState = Schemas["StateEnum"];
export type ServerWrite = Schemas["ServerWriteRequest"];
export type CatalogQuery = NonNullable<operations["servers_list"]["parameters"]["query"]>;
export type StatsRange = "24h" | "7d";

export const editions: Edition[] = ["java", "bedrock", "both"];
export const languages: Language[] = ["uk", "multi", "en"];
export const modes: Mode[] = [
  "survival",
  "smp",
  "creative",
  "anarchy",
  "rp",
  "minigames",
  "skyblock",
  "pvp",
  "modded",
  "hardcore",
];
export const MAX_MODES = 5;
