import { describe as group, expect, it } from "vitest";

import { describe } from "./format";
import type { Notification } from "./types";

const base: Notification = {
  id: 1,
  type: "restored",
  payload: { kind: "skin", id: "7", title: "Мавка" },
  is_read: false,
  created_at: "2026-10-18T10:00:00Z",
};

group("notification text", () => {
  it("links to the object", () => {
    expect(describe(base)).toEqual({
      text: "«Мавка» знову доступний: скарги не підтвердилися.",
      href: "/skins/7",
    });
  });

  it("explains hidden objects", () => {
    expect(
      describe({
        ...base,
        type: "hidden",
        payload: { kind: "server", id: "sich", title: "Січ" },
      }),
    ).toEqual({
      text: "«Січ» приховано після скарг. Модератори вирішили, що він порушує правила.",
      href: "/servers/sich",
    });
  });

  it("has no link for warnings", () => {
    expect(describe({ ...base, type: "warning", payload: { reason: "Образи" } })).toEqual({
      text: "Попередження від модераторів: Образи",
      href: null,
    });
  });
});
