import { describe as group, expect, it } from "vitest";

import { describe } from "./format";
import type { Notification } from "./types";

const base: Notification = {
  id: 1,
  type: "approved",
  payload: { kind: "skin", id: "7", title: "Мавка" },
  is_read: false,
  created_at: "2026-10-18T10:00:00Z",
};

group("notification text", () => {
  it("links to the object", () => {
    expect(describe(base)).toEqual({
      text: "«Мавка» опубліковано — тепер його бачать усі.",
      href: "/skins/7",
    });
  });

  it("explains rejections and hidden comments", () => {
    expect(
      describe({ ...base, type: "rejected", payload: { ...base.payload, reason: "Чужий" } }).text,
    ).toBe("«Мавка» не пройшов модерацію: Чужий");
    expect(
      describe({
        ...base,
        type: "hidden",
        payload: { kind: "server", id: "sich", excerpt: "спам" },
      }),
    ).toEqual({ text: "Твій коментар «спам» приховано після скарг.", href: "/servers/sich" });
  });

  it("has no link for warnings", () => {
    expect(describe({ ...base, type: "warning", payload: { reason: "Образи" } })).toEqual({
      text: "Попередження від модераторів: Образи",
      href: null,
    });
  });
});
