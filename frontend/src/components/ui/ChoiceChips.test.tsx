import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { ChoiceChips } from "./ChoiceChips";

const loaders = [
  { value: "fabric", label: "Fabric" },
  { value: "forge", label: "Forge" },
] as const;

function Single() {
  const [value, setValue] = useState<"fabric" | "forge" | "">("");
  return <ChoiceChips label="Лоадер" options={[...loaders]} value={value} onChange={setValue} />;
}

function Multiple() {
  const [value, setValue] = useState<Array<"fabric" | "forge">>(["fabric"]);
  return (
    <ChoiceChips
      multiple
      label="Лоадери"
      options={[...loaders]}
      value={value}
      onChange={setValue}
    />
  );
}

describe("ChoiceChips", () => {
  it("works as a radio group", async () => {
    const user = userEvent.setup();
    render(<Single />);

    expect(screen.getByRole("group", { name: "Лоадер" })).toBeInTheDocument();
    await user.click(screen.getByText("Forge"));

    expect(screen.getByRole("radio", { name: "Forge" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Fabric" })).not.toBeChecked();
  });

  it("toggles several values when multiple", async () => {
    const user = userEvent.setup();
    render(<Multiple />);

    await user.click(screen.getByText("Forge"));
    expect(screen.getByRole("checkbox", { name: "Fabric" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Forge" })).toBeChecked();

    await user.click(screen.getByText("Fabric"));
    expect(screen.getByRole("checkbox", { name: "Fabric" })).not.toBeChecked();
  });
});
