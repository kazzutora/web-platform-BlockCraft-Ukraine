import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type ProjectType = Schemas["ProjectTypeEnum"];
export type ProjectCard = Schemas["ProjectCard"];
export type ProjectDetail = Schemas["ProjectDetail"];
export type ProjectVersion = Schemas["ProjectVersion"];
export type Versions = Schemas["Versions"];
export type Category = Schemas["Category"];
export type CatalogPage = Schemas["PaginatedProjectCardList"];
export type CatalogQuery = NonNullable<operations["mods_list"]["parameters"]["query"]>;

export const projectTypes: ProjectType[] = ["mod", "resourcepack", "shader"];
