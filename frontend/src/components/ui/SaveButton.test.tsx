import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SaveButton } from "./SaveButton";

describe("SaveButton", () => {
  it("toggles its own state and reports it", async () => {
    const user = userEvent.setup();
    const onSavedChange = vi.fn();
    render(<SaveButton onSavedChange={onSavedChange} />);
    const button = screen.getByRole("button", { name: "Зберегти" });

    await user.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(onSavedChange).toHaveBeenLastCalledWith(true);

    await user.click(button);
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(onSavedChange).toHaveBeenLastCalledWith(false);
  });

  it("follows the controlled value", async () => {
    const user = userEvent.setup();
    const onSavedChange = vi.fn();
    render(<SaveButton saved={false} onSavedChange={onSavedChange} count={12} />);
    const button = screen.getByRole("button", { name: "Зберегти" });

    await user.click(button);

    expect(onSavedChange).toHaveBeenCalledWith(true);
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(button).toHaveTextContent("12");
  });
});
