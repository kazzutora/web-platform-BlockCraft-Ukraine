import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Button } from "./Button";
import { Dialog } from "./Dialog";

function renderDialog() {
  return render(
    <Dialog
      title="Нова колекція"
      description="Назви колекцію"
      trigger={<Button>Створити колекцію</Button>}
    >
      <input aria-label="Назва" />
    </Dialog>,
  );
}

describe("Dialog", () => {
  it("opens from the trigger as an accessible modal dialog", async () => {
    const user = userEvent.setup();
    renderDialog();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Створити колекцію" }));

    const dialog = screen.getByRole("dialog", { name: "Нова колекція" });
    expect(dialog).toHaveAccessibleDescription("Назви колекцію");
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    renderDialog();
    const trigger = screen.getByRole("button", { name: "Створити колекцію" });

    await user.click(trigger);
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes with the close button", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("button", { name: "Створити колекцію" }));
    await user.click(screen.getByRole("button", { name: "Закрити" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
