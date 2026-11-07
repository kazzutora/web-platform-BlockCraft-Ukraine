import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SourceBadge } from "./SourceBadge";

describe("SourceBadge", () => {
  it("links to the source in a new tab without leaking the opener", () => {
    render(
      <SourceBadge
        name="Modrinth"
        url="https://modrinth.com/mod/sodium"
        label="Sodium на Modrinth"
      />,
    );

    const link = screen.getByRole("link", { name: "Sodium на Modrinth" });
    expect(link).toHaveAttribute("href", "https://modrinth.com/mod/sodium");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener");
    expect(link).toHaveTextContent("Modrinth↗");
  });
});
