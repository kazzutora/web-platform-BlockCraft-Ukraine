import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/components/ui/ToastProvider";
import { AuthPromptProvider } from "@/features/auth/AuthPromptProvider";
import { api } from "@/lib/api/client";

import { SaveToggle } from "./SaveToggle";

const session = vi.hoisted(() => ({ me: null as { nickname: string } | null }));

vi.mock("@/features/auth/useMe", () => ({ useMe: () => ({ me: session.me }) }));
vi.mock("@/lib/api/client", () => ({ api: { POST: vi.fn(), DELETE: vi.fn() } }));

const post = vi.mocked(api.POST);

function renderToggle() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AuthPromptProvider>
          <SaveToggle kind="mod" id="lithium" saved={false} count={4} />
        </AuthPromptProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("SaveToggle", () => {
  beforeEach(() => {
    post.mockReset();
    session.me = { nickname: "Alex_UA" };
  });

  it("fills the slot at once and sends the save", async () => {
    let finish: (value: unknown) => void = () => {};
    post.mockReturnValue(new Promise((resolve) => (finish = resolve)) as never);
    renderToggle();
    const button = screen.getByRole("button", { name: "Зберегти" });

    await userEvent.setup().click(button);

    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(button).toHaveTextContent("5");
    expect(post).toHaveBeenCalledWith("/api/v1/favorites", {
      body: { kind: "mod", id: "lithium" },
    });
    finish({ data: { favorited: true, favorites_count: 5 }, response: new Response() });
  });

  it("rolls back and shows a toast when the API fails", async () => {
    post.mockResolvedValue({ response: new Response(null, { status: 500 }) } as never);
    renderToggle();
    const button = screen.getByRole("button", { name: "Зберегти" });

    await userEvent.setup().click(button);

    expect(await screen.findByText("Не вдалося зберегти. Спробуй ще раз.")).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(button).toHaveTextContent("4");
  });

  it("asks guests to sign in instead of saving", async () => {
    session.me = null;
    renderToggle();

    await userEvent.setup().click(screen.getByRole("button", { name: "Зберегти" }));

    expect(screen.getByRole("dialog", { name: "Увійди, щоб не загубити" })).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });
});
