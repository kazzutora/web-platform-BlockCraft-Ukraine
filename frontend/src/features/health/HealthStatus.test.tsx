import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getHealth } from "./api";
import { HealthStatus } from "./HealthStatus";

vi.mock("./api", () => ({ getHealth: vi.fn() }));

describe("HealthStatus", () => {
  it("shows ok and every check when the API is healthy", async () => {
    vi.mocked(getHealth).mockResolvedValue({
      status: "ok",
      checks: { database: "ok", redis: "ok" },
    });

    render(await HealthStatus());

    expect(screen.getByRole("status")).toHaveTextContent("Статус API: ok");
    expect(screen.getByText("База даних").nextSibling).toHaveTextContent("ok");
    expect(screen.getByText("Redis").nextSibling).toHaveTextContent("ok");
  });

  it("shows which check failed", async () => {
    vi.mocked(getHealth).mockResolvedValue({
      status: "error",
      checks: { database: "ok", redis: "error" },
    });

    render(await HealthStatus());

    expect(screen.getByRole("status")).toHaveTextContent("Статус API: error");
    expect(screen.getByText("Redis").nextSibling).toHaveTextContent("error");
  });

  it("explains when the API is unreachable", async () => {
    vi.mocked(getHealth).mockResolvedValue(null);

    render(await HealthStatus());

    expect(screen.getByRole("status")).toHaveTextContent("API недоступне");
  });
});
