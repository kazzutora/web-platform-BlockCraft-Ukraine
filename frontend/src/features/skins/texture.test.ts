import { describe, expect, it } from "vitest";

import { checkDimensions, checkFile, detectModel } from "./texture";

function texture({ slim = false } = {}): Uint8ClampedArray {
  const pixels = new Uint8ClampedArray(64 * 64 * 4).fill(255);
  if (slim) {
    for (let y = 20; y < 32; y += 1) {
      for (let x = 54; x < 56; x += 1) pixels[(y * 64 + x) * 4 + 3] = 0;
    }
  }
  return pixels;
}

describe("skin file checks", () => {
  it("accepts small PNG files only", () => {
    expect(checkFile({ type: "image/png", name: "steve.png", size: 3000 })).toBeNull();
    expect(checkFile({ type: "image/jpeg", name: "steve.jpg", size: 3000 })).toMatch(/PNG/);
    expect(checkFile({ type: "image/png", name: "big.png", size: 200 * 1024 })).toMatch(/100 КБ/);
  });

  it("accepts 64×64 and legacy 64×32 textures", () => {
    expect(checkDimensions(64, 64)).toBeNull();
    expect(checkDimensions(64, 32)).toBeNull();
    expect(checkDimensions(128, 128)).toMatch(/128×128/);
  });

  it("detects slim arms by the empty fourth column", () => {
    expect(detectModel(texture({ slim: true }), 64)).toBe("slim");
    expect(detectModel(texture(), 64)).toBe("classic");
    expect(detectModel(texture({ slim: true }), 32)).toBe("classic");
  });
});
