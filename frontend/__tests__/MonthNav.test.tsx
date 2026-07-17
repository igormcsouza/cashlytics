import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import MonthNav from "@/components/MonthNav";

afterEach(() => cleanup());

describe("MonthNav", () => {
  it("shows the current month and calls onPrev/onNext", async () => {
    const user = userEvent.setup();
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(<MonthNav month="2026-07" onPrev={onPrev} onNext={onNext} />);

    expect(screen.getByText("July 2026")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Previous month" }));
    expect(onPrev).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Next month" }));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it("renders faded neighboring months hidden on mobile via responsive classes", () => {
    render(<MonthNav month="2026-07" onPrev={() => {}} onNext={() => {}} />);

    const prev = screen.getByText("June 2026");
    const next = screen.getByText("August 2026");
    expect(prev.className).toContain("hidden");
    expect(prev.className).toContain("sm:inline");
    expect(next.className).toContain("hidden");
    expect(next.className).toContain("sm:inline");
  });
});
