import { afterEach, describe, expect, it, vi } from "vitest";

import { rememberPendingAction, takePendingAction } from "./pending-action";

describe("pending action", () => {
  afterEach(() => {
    sessionStorage.clear();
    vi.useRealTimers();
  });

  it("is taken once on the same page", () => {
    rememberPendingAction("save:mod:sodium", "/mods/sodium");

    expect(takePendingAction("save:mod:sodium", "/mods/sodium")).toBe(true);
    expect(takePendingAction("save:mod:sodium", "/mods/sodium")).toBe(false);
  });

  it("does not fire for another action or page", () => {
    rememberPendingAction("save:mod:sodium", "/mods/sodium");

    expect(takePendingAction("save:mod:iris", "/mods/sodium")).toBe(false);
    expect(takePendingAction("save:mod:sodium", "/mods/iris")).toBe(false);
  });

  it("expires after 30 minutes", () => {
    vi.useFakeTimers();
    rememberPendingAction("save:mod:sodium", "/mods/sodium");
    vi.advanceTimersByTime(31 * 60 * 1000);

    expect(takePendingAction("save:mod:sodium", "/mods/sodium")).toBe(false);
  });
});
