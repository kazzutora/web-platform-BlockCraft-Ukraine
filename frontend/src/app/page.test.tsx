import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "./page";

vi.mock("@/features/game/GameChipArea", () => ({ GameChipArea: () => null }));

vi.mock("@/features/home/HomeSections", () => ({
  HomeSections: () => <section aria-label="sections" />,
}));

describe("HomePage", () => {
  it("renders the hero with a search that works without JavaScript", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Збери свій Minecraft");
    const search = screen.getByRole("search");
    expect(search).toHaveAttribute("action", "/search");
    expect(screen.getByRole("searchbox", { name: "Знайти мод, скін або сервер" })).toHaveAttribute(
      "name",
      "q",
    );
  });
});
