import { describe, expect, it } from "vitest";

import { nicknameSchema, registerSchema } from "./schemas";

describe("nicknameSchema", () => {
  it.each(["Steve_UA", "abc", "x".repeat(24)])("accepts %s", (nickname) => {
    expect(nicknameSchema.safeParse(nickname).success).toBe(true);
  });

  it.each(["ab", "x".repeat(25), "Стів", "steve.ua", "steve ua"])("rejects %s", (nickname) => {
    expect(nicknameSchema.safeParse(nickname).success).toBe(false);
  });
});

describe("registerSchema", () => {
  it("requires a valid email and a password of 8+ characters", () => {
    const result = registerSchema.safeParse({
      email: "steve@",
      username: "Steve",
      password: "short",
    });

    expect(result.success).toBe(false);
    const fields = result.error?.issues.map((issue) => issue.path[0]);
    expect(fields).toEqual(["email", "password"]);
  });
});
