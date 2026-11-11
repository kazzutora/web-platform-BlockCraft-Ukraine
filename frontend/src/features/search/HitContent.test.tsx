import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HitContent } from "./HitContent";
import type { SearchHit } from "./types";

const hit: SearchHit = {
  kind: "mod",
  id: "sodium",
  title: "Sodium",
  summary: "",
  image: null,
  project_type: "mod",
  latest_game_version: "26.3",
  loaders: ["fabric"],
  author: null,
  modes: [],
  color_bucket: null,
  address: null,
  items_count: null,
  fits_my_game: false,
};

describe("HitContent", () => {
  it("marks a hit that does not fit «Моя гра»", () => {
    render(<HitContent hit={hit} gameLabel="1.21.1 · Forge" />);

    expect(screen.getByText(/не для 1\.21\.1 · Forge/)).toBeInTheDocument();
  });

  it("has no mark when it fits or nothing is chosen", () => {
    const { rerender } = render(<HitContent hit={{ ...hit, fits_my_game: true }} />);
    expect(screen.queryByText(/не для/)).toBeNull();

    rerender(<HitContent hit={{ ...hit, fits_my_game: null }} />);
    expect(screen.queryByText(/не для/)).toBeNull();
  });
});
