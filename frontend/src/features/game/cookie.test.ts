import { describe, expect, it } from "vitest";

import { formatGameCookie, parseGameCookie } from "./cookie";

describe("bc_game cookie", () => {
  it("reads version and loader, either may be empty", () => {
    expect(parseGameCookie("1.21.1:fabric")).toEqual({ game_version: "1.21.1", loader: "fabric" });
    expect(parseGameCookie("1.21.1%3Afabric")).toEqual({
      game_version: "1.21.1",
      loader: "fabric",
    });
    expect(parseGameCookie("26.3:")).toEqual({ game_version: "26.3", loader: "" });
    expect(parseGameCookie(":neoforge")).toEqual({ game_version: "", loader: "neoforge" });
  });

  it("ignores anything else", () => {
    for (const value of [":", "1.21.1", "1.21.1:optifine", "<b>:fabric", "%E0:", "", undefined]) {
      expect(parseGameCookie(value)).toBeNull();
    }
  });

  it("round-trips", () => {
    const game = { game_version: "1.20.1", loader: "forge" };
    expect(parseGameCookie(formatGameCookie(game))).toEqual(game);
  });
});
