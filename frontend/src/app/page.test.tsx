import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "./page";

vi.mock("@/features/health/HealthStatus", () => ({
  HealthStatus: () => <p role="status">health</p>,
}));

describe("HomePage", () => {
  it("renders the title and the health status", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("BlockCraft Ukraine");
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
