import { describe, expect, it } from "vitest";

import { compatCopy } from "./copy";

describe("compatCopy", () => {
  it("counts warnings in Ukrainian", () => {
    expect(compatCopy.status.warnings(1)).toBe("1 попередження");
    expect(compatCopy.status.warnings(3)).toBe("3 попередження");
    expect(compatCopy.status.warnings(7)).toBe("7 попереджень");
    expect(compatCopy.status.warnings(21)).toBe("21 попередження");
  });

  it("explains every warning code with the project names", () => {
    expect(compatCopy.warning.optifine_manual({ project: "BSL" })).toContain("BSL");
    expect(compatCopy.warning.version_mismatch({ project: "Sodium", required_by: "Iris" })).toMatch(
      /^Iris просить іншу версію Sodium/,
    );
    expect(compatCopy.reason.implicit("Complementary", "Fabric")).toContain("на Fabric");
  });
});
