import { describe, expect, it } from "vitest";

import { downloadTarget } from "./target";
import type { ProjectDetail } from "./types";

const sodium = {
  project_type: "mod",
  game_versions: ["1.21.1", "26.3"],
  latest_game_version: "26.3",
  loaders: ["babric", "fabric", "neoforge"],
} as unknown as ProjectDetail;

describe("downloadTarget", () => {
  it("prefers the URL", () => {
    expect(downloadTarget(sodium, { game_version: "1.21.1", loader: "neoforge" }, null)).toEqual({
      gameVersion: "1.21.1",
      loader: "neoforge",
      label: "1.21.1 · NeoForge",
    });
  });

  it("then the game profile when the project supports it", () => {
    const target = downloadTarget(sodium, {}, { game_version: "1.21.1", loader: "neoforge" });
    expect(target.label).toBe("1.21.1 · NeoForge");

    const unsupported = downloadTarget(sodium, {}, { game_version: "1.8.9", loader: "forge" });
    expect(unsupported.label).toBe("26.3 · Fabric");
  });

  it("ignores the loader for shaders", () => {
    const shader = { ...sodium, project_type: "shader", loaders: ["iris"] } as ProjectDetail;

    expect(downloadTarget(shader, { loader: "fabric" }, null)).toEqual({
      gameVersion: "26.3",
      loader: "",
      label: "26.3",
    });
  });
});
