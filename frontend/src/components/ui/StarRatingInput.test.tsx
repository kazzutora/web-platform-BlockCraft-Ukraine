import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StarRatingInput } from "./StarRatingInput";

describe("StarRatingInput", () => {
  it("is a radio group named by its label", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(<StarRatingInput label="Твоя оцінка" name="stars" onValueChange={onValueChange} />);

    expect(screen.getByRole("group", { name: "Твоя оцінка" })).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "4 з 5" }));

    expect(screen.getByRole("radio", { name: "4 з 5" })).toBeChecked();
    expect(onValueChange).toHaveBeenCalledWith(4);
  });

  it("changes the value with arrow keys", async () => {
    const user = userEvent.setup();
    render(<StarRatingInput label="Твоя оцінка" name="stars" defaultValue={3} />);

    await user.tab();
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("radio", { name: "4 з 5" })).toBeChecked();
  });
});
