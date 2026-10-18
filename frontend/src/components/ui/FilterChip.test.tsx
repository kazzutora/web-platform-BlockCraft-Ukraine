import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { FilterChip } from "./FilterChip";

function ToggleChip() {
  const [active, setActive] = useState(false);
  return (
    <FilterChip active={active} onClick={() => setActive((value) => !value)}>
      Fabric
    </FilterChip>
  );
}

describe("FilterChip", () => {
  it("toggles aria-pressed when used as a button", async () => {
    const user = userEvent.setup();
    render(<ToggleChip />);
    const chip = screen.getByRole("button", { name: "Fabric" });
    expect(chip).toHaveAttribute("aria-pressed", "false");

    await user.click(chip);
    expect(chip).toHaveAttribute("aria-pressed", "true");
    expect(chip).toHaveClass("bg-text", "text-bg");

    await user.click(chip);
    expect(chip).toHaveAttribute("aria-pressed", "false");
  });

  it("is a link marked as current when filters live in the URL", () => {
    render(
      <>
        <FilterChip href="/mods?loader=fabric" active>
          Fabric
        </FilterChip>
        <FilterChip href="/mods?loader=forge" active={false}>
          Forge
        </FilterChip>
      </>,
    );

    expect(screen.getByRole("link", { name: "Fabric" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: "Forge" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Forge" })).toHaveAttribute(
      "href",
      "/mods?loader=forge",
    );
  });
});
