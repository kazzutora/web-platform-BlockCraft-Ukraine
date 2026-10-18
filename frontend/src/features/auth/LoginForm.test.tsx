import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { auth } from "@/lib/api/auth-client";

import { LoginForm } from "./LoginForm";

const signedIn = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("next=/me/settings"),
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("./useSignedIn", () => ({ useSignedIn: () => signedIn }));
vi.mock("@/lib/api/auth-client", () => ({ auth: { GET: vi.fn(), POST: vi.fn() } }));

const post = vi.mocked(auth.POST);

function renderForm() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  vi.mocked(auth.GET).mockResolvedValue({
    data: { status: 200, data: { socialaccount: { providers: [] } } },
    response: new Response(),
  } as never);
  return render(
    <QueryClientProvider client={client}>
      <LoginForm />
    </QueryClientProvider>,
  );
}

async function submit(email = "steve@example.com", password = "Creeper-2026") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Пароль"), password);
  await user.click(screen.getByRole("button", { name: "Увійти" }));
}

describe("LoginForm", () => {
  beforeEach(() => {
    post.mockReset();
    signedIn.mockReset();
  });

  it("validates the email before calling the API", async () => {
    renderForm();

    await submit("steve@");

    expect(await screen.findByText("Введи коректну адресу.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("signs in and returns to `next`", async () => {
    post.mockResolvedValue({ data: {}, response: new Response(null, { status: 200 }) } as never);
    renderForm();

    await submit();

    expect(post).toHaveBeenCalledWith("/_allauth/browser/v1/auth/login", {
      body: { email: "steve@example.com", password: "Creeper-2026" },
    });
    expect(signedIn).toHaveBeenCalledWith("/me/settings");
  });

  it("asks to confirm the email when the account is not verified", async () => {
    post.mockResolvedValue({
      error: { status: 401, data: { flows: [{ id: "verify_email", is_pending: true }] } },
      response: new Response(null, { status: 401 }),
    } as never);
    renderForm();

    await submit();

    expect(await screen.findByText(/Спершу підтверди пошту/)).toBeInTheDocument();
    expect(signedIn).not.toHaveBeenCalled();
  });

  it("shows the server error for the whole form", async () => {
    post.mockResolvedValue({
      error: {
        status: 400,
        errors: [{ code: "email_password_mismatch", message: "Email або пароль невірні." }],
      },
      response: new Response(null, { status: 400 }),
    } as never);
    renderForm();

    await submit();

    expect(await screen.findByRole("alert")).toHaveTextContent("Email або пароль невірні.");
  });
});
