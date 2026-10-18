import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./Button";

describe("Button", () => {
  it("is a real button of type button by default", () => {
    render(<Button>Зберегти</Button>);

    const button = screen.getByRole("button", { name: "Зберегти" });
    expect(button).toHaveAttribute("type", "button");
  });

  it("calls onClick when pressed with the mouse or keyboard", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Зберегти</Button>);

    await user.click(screen.getByRole("button"));
    await user.keyboard("{Enter}");

    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("is disabled and busy while loading", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Зберігаємо…
      </Button>,
    );

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("applies the variant and size styles", () => {
    render(
      <Button variant="secondary" size="lg">
        В колекцію
      </Button>,
    );

    const button = screen.getByRole("button");
    expect(button).toHaveClass("border", "border-text", "h-12");
  });
});
