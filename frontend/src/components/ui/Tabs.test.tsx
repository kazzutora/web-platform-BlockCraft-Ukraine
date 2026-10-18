import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Tabs } from "./Tabs";

const items = [
  { value: "about", label: "Опис", content: <p>Про мод</p> },
  { value: "versions", label: "Версії", content: <p>Список версій</p> },
  { value: "reviews", label: "Відгуки", content: <p>Відгуки гравців</p> },
];

describe("Tabs", () => {
  it("shows the first tab by default", () => {
    render(<Tabs label="Сторінка мода" items={items} />);

    expect(screen.getByRole("tablist", { name: "Сторінка мода" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Опис" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Про мод");
  });

  it("switches the panel on click", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(<Tabs label="Сторінка мода" items={items} onValueChange={onValueChange} />);

    await user.click(screen.getByRole("tab", { name: "Версії" }));

    expect(screen.getByRole("tab", { name: "Версії" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Список версій");
    expect(onValueChange).toHaveBeenCalledWith("versions");
  });

  it("moves between tabs with arrow keys", async () => {
    const user = userEvent.setup();
    render(<Tabs label="Сторінка мода" items={items} />);

    await user.tab();
    expect(screen.getByRole("tab", { name: "Опис" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");

    const versions = screen.getByRole("tab", { name: "Версії" });
    expect(versions).toHaveFocus();
    expect(versions).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Список версій");
  });
});
