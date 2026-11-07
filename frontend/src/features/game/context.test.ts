import { beforeEach, describe, expect, it, vi } from "vitest";

const jar = new Map<string, string>();
const getMyGame = vi.fn();
const supported = vi.fn();

vi.mock("next/headers", () => ({
  cookies: async () => ({
    has: (name: string) => jar.has(name),
    get: (name: string) => (jar.has(name) ? { name, value: jar.get(name) } : undefined),
  }),
}));
vi.mock("@/lib/api/server-client", () => ({
  getServerClient: async () => ({ GET: getMyGame }),
}));
vi.mock("./meta", () => ({ getGameVersions: () => supported() }));

const { getGameContext } = await import("./context");

describe("getGameContext", () => {
  beforeEach(() => {
    jar.clear();
    getMyGame.mockReset();
    supported.mockReset().mockResolvedValue(["26.3", "1.21.1", "1.20.1"]);
  });

  it("is empty without a profile or a cookie", async () => {
    expect(await getGameContext()).toEqual({ game_version: "", loader: "", source: "none" });
    expect(getMyGame).not.toHaveBeenCalled();
  });

  it("reads a guest's cookie", async () => {
    jar.set("bc_game", "1.21.1%3Afabric");

    expect(await getGameContext()).toEqual({
      game_version: "1.21.1",
      loader: "fabric",
      source: "cookie",
    });
  });

  it("prefers the profile once it has a choice", async () => {
    jar.set("sessionid", "x");
    jar.set("bc_game", "1.21.1:fabric");
    getMyGame.mockResolvedValue({ data: { game_version: "26.3", loader: "neoforge" } });

    expect(await getGameContext()).toEqual({
      game_version: "26.3",
      loader: "neoforge",
      source: "profile",
    });
  });

  it("falls back to the cookie for an empty profile or an expired session", async () => {
    jar.set("sessionid", "x");
    jar.set("bc_game", ":quilt");
    getMyGame.mockResolvedValueOnce({ data: { game_version: null, loader: "" } });
    expect((await getGameContext()).source).toBe("cookie");

    getMyGame.mockResolvedValueOnce({ data: undefined, response: { status: 401 } });
    expect(await getGameContext()).toEqual({ game_version: "", loader: "quilt", source: "cookie" });
  });

  it("drops a version that is not supported", async () => {
    jar.set("bc_game", "1.15.2:fabric");
    expect(await getGameContext()).toEqual({
      game_version: "",
      loader: "fabric",
      source: "cookie",
    });

    jar.set("bc_game", "1.15.2:");
    expect((await getGameContext()).source).toBe("none");
  });

  it("keeps the version when the list of versions is unavailable", async () => {
    supported.mockResolvedValue([]);
    jar.set("bc_game", "1.21.1:");

    expect((await getGameContext()).game_version).toBe("1.21.1");
  });
});
