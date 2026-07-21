import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ExpenseTable from "@/components/ExpenseTable";
import type { Expense } from "@/lib/types";

const EXPENSES: Expense[] = [
  {
    id: "1",
    description: "Rent",
    deadline: "2000-01-01",
    value: 1500,
    recurrent: true,
    paid: false,
  },
  {
    id: "2",
    description: "Coffee",
    deadline: "2026-07-05",
    value: 4.5,
    recurrent: false,
    paid: true,
  },
];

afterEach(() => cleanup());

describe("ExpenseTable", () => {
  it("renders rows in a single-line flex actions layout on all breakpoints", () => {
    render(
      <ExpenseTable
        expenses={EXPENSES}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onTogglePaid={vi.fn()}
      />,
    );

    const rentRow = screen.getByText("Rent").closest("tr") as HTMLElement;
    const actionsDiv = rentRow.querySelector("td:last-child > div");
    expect(actionsDiv?.className).toContain("flex");
    expect(actionsDiv?.className).not.toContain("grid-cols-2");
  });

  it("calls onEdit exactly once when a row is double-clicked", () => {
    const onEdit = vi.fn();
    render(
      <ExpenseTable
        expenses={EXPENSES}
        onEdit={onEdit}
        onDelete={vi.fn()}
        onTogglePaid={vi.fn()}
      />,
    );

    const rentRow = screen.getByText("Rent").closest("tr") as HTMLElement;
    fireEvent.doubleClick(rentRow);

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledWith(EXPENSES[0]);
  });

  it("does not call onEdit when an action button is double-clicked, but still handles a single click", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const onTogglePaid = vi.fn();
    render(
      <ExpenseTable
        expenses={EXPENSES}
        onEdit={onEdit}
        onDelete={vi.fn()}
        onTogglePaid={onTogglePaid}
      />,
    );

    const toggleButton = screen.getAllByRole("button", {
      name: /mark as (paid|unpaid)/i,
    })[0];

    fireEvent.doubleClick(toggleButton);
    expect(onEdit).not.toHaveBeenCalled();

    await user.click(toggleButton);
    expect(onTogglePaid).toHaveBeenCalledTimes(1);
    expect(onTogglePaid).toHaveBeenCalledWith(EXPENSES[0]);
  });

  it("still calls onEdit on a single click of the edit button", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    render(
      <ExpenseTable
        expenses={EXPENSES}
        onEdit={onEdit}
        onDelete={vi.fn()}
        onTogglePaid={vi.fn()}
      />,
    );

    const editButtons = screen.getAllByRole("button", {
      name: /edit expense/i,
    });
    await user.click(editButtons[0]);

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledWith(EXPENSES[0]);
  });
});
