import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Login from "@/app/login/page";
import * as auth from "@/lib/auth";

vi.mock("@/lib/auth");

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

const mocked = vi.mocked(auth);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.login.mockResolvedValue({ status: "ok" });
  mocked.completeNewPassword.mockResolvedValue();
});

afterEach(() => cleanup());

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(
    screen.getByPlaceholderText("you@example.com"),
    "admin@cashlytics.dev",
  );
  await user.type(screen.getByPlaceholderText("••••••••"), "password");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("Login", () => {
  it("logs in and redirects home", async () => {
    const user = userEvent.setup();
    render(<Login />);

    await fillAndSubmit(user);

    await waitFor(() =>
      expect(mocked.login).toHaveBeenCalledWith(
        "admin@cashlytics.dev",
        "password",
      ),
    );
    expect(replace).toHaveBeenCalledWith("/");
  });

  it("shows the error when login fails", async () => {
    mocked.login.mockRejectedValue(new Error("Incorrect username or password."));
    const user = userEvent.setup();
    render(<Login />);

    await fillAndSubmit(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Incorrect username or password.",
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("asks for a new password on first login and completes the challenge", async () => {
    mocked.login.mockResolvedValue({
      status: "new_password_required",
      session: "session-token",
    });
    const user = userEvent.setup();
    render(<Login />);

    await fillAndSubmit(user);

    expect(
      await screen.findByText("Choose a new password"),
    ).toBeInTheDocument();

    const [newPw, confirmPw] = screen.getAllByPlaceholderText("••••••••");
    await user.type(newPw, "my-own-password");
    await user.type(confirmPw, "my-own-password");
    await user.click(
      screen.getByRole("button", { name: "Set password and sign in" }),
    );

    await waitFor(() =>
      expect(mocked.completeNewPassword).toHaveBeenCalledWith(
        "admin@cashlytics.dev",
        "my-own-password",
        "session-token",
      ),
    );
    expect(replace).toHaveBeenCalledWith("/");
  });

  it("rejects mismatched new passwords without calling Cognito", async () => {
    mocked.login.mockResolvedValue({
      status: "new_password_required",
      session: "session-token",
    });
    const user = userEvent.setup();
    render(<Login />);

    await fillAndSubmit(user);
    await screen.findByText("Choose a new password");

    const [newPw, confirmPw] = screen.getAllByPlaceholderText("••••••••");
    await user.type(newPw, "one-password");
    await user.type(confirmPw, "another-password");
    await user.click(
      screen.getByRole("button", { name: "Set password and sign in" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Passwords do not match.",
    );
    expect(mocked.completeNewPassword).not.toHaveBeenCalled();
  });
});
