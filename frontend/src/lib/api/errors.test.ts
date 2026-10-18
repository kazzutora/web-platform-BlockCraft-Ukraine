import { describe, expect, it } from "vitest";

import { fieldErrors, generalError } from "./errors";

describe("fieldErrors", () => {
  it("reads our API format", () => {
    const error = {
      detail: "Перевір введені дані.",
      code: "invalid",
      fields: { mc_nickname: ["Нік у Minecraft: 3–16 символів."], bio: ["Задовго.", "Ще одна"] },
    };

    expect(fieldErrors(error)).toEqual({
      mc_nickname: "Нік у Minecraft: 3–16 символів.",
      bio: "Задовго.",
    });
  });

  it("reads allauth errors and renames params", () => {
    const error = {
      status: 400,
      errors: [
        { code: "username_taken", message: "Нік зайнятий.", param: "username" },
        { code: "invalid", message: "Друга помилка.", param: "username" },
        { code: "too_many", message: "Забагато спроб." },
      ],
    };

    expect(fieldErrors(error, { username: "nickname" })).toEqual({
      nickname: "Нік зайнятий.",
      root: "Забагато спроб.",
    });
  });

  it("ignores values that are not error bodies", () => {
    expect(fieldErrors(undefined)).toEqual({});
    expect(fieldErrors("boom")).toEqual({});
  });
});

describe("generalError", () => {
  it("prefers errors without a field", () => {
    expect(generalError({ errors: [{ code: "x", message: "Невірний пароль." }] }, "fallback")).toBe(
      "Невірний пароль.",
    );
  });

  it("uses our detail when there are no field errors", () => {
    expect(generalError({ detail: "Не знайдено.", code: "not_found", fields: {} }, "fb")).toBe(
      "Не знайдено.",
    );
  });

  it("falls back otherwise", () => {
    expect(generalError(null, "Щось пішло не так.")).toBe("Щось пішло не так.");
  });
});
