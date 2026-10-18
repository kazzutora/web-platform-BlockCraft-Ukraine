import { describe, expect, it } from "vitest";

import { safeNext } from "./next-url";

describe("safeNext", () => {
  it.each(["/me/settings", "/mods?loader=fabric", "/u/Steve_UA"])("keeps %s", (next) => {
    expect(safeNext(next)).toBe(next);
  });

  it.each([
    ["https://evil.example", "absolute URL"],
    ["//evil.example", "protocol-relative URL"],
    ["/\\evil.example", "backslash trick"],
    ["javascript:alert(1)", "script URL"],
    ["", "empty"],
    [null, "missing"],
  ])("rejects %s (%s)", (next, reason) => {
    expect(safeNext(next), reason).toBe("/");
  });
});
