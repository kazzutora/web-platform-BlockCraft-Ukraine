import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompatStatus } from "./CompatStatus";

describe("CompatStatus", () => {
  it("says the status in words next to the coloured mark", () => {
    render(<CompatStatus tone="warning">2 попередження</CompatStatus>);

    const status = screen.getByText("2 попередження");
    expect(status).toHaveClass("text-warning");
    expect(status.querySelector("[aria-hidden]")).toHaveClass("bg-warning");
  });
});
