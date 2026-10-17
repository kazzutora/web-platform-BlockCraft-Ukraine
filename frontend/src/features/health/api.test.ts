// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";

import { getHealth } from "./api";

vi.mock("next/headers", () => ({
  cookies: async () => ({ toString: () => "" }),
}));
vi.mock("next/server", () => ({ connection: async () => undefined }));

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("getHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the report when the API is healthy", async () => {
    const report = { status: "ok", checks: { database: "ok", redis: "ok" } };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(report, 200)),
    );

    await expect(getHealth()).resolves.toEqual(report);
  });

  it("returns the report body for 503", async () => {
    const report = { status: "error", checks: { database: "ok", redis: "error" } };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(report, 503)),
    );

    await expect(getHealth()).resolves.toEqual(report);
  });

  it("returns null when the API is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("fetch failed");
      }),
    );

    await expect(getHealth()).resolves.toBeNull();
  });
});
