import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Home from "@/app/page";
import * as api from "@/lib/api";
import type { Expense } from "@/lib/types";

vi.mock("@/lib/api");

const mocked = vi.mocked(api);

const EXPENSES: Expense[] = [
  {
    id: "1",
    description: "Rent",
    deadline: "2026-07-01",
    value: 1500,
    recurrent: true,
  },
  {
    id: "2",
    description: "Coffee",
    deadline: "2026-07-05",
    value: 4.5,
    recurrent: false,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  mocked.listExpenses.mockResolvedValue([...EXPENSES]);
  mocked.createExpense.mockResolvedValue(EXPENSES[0]);
  mocked.updateExpense.mockResolvedValue(EXPENSES[0]);
  mocked.deleteExpense.mockResolvedValue();
});

afterEach(() => cleanup());

describe("Home", () => {
  it("renders the list of expenses", async () => {
    render(<Home />);
    expect(await screen.findByText("Rent")).toBeInTheDocument();
    expect(screen.getByText("Coffee")).toBeInTheDocument();
  });

  it("shows the empty state when there are no expenses", async () => {
    mocked.listExpenses.mockResolvedValue([]);
    render(<Home />);
    expect(
      await screen.findByText(/No expenses yet/i),
    ).toBeInTheDocument();
  });

  it("computes the total of all expenses", async () => {
    render(<Home />);
    await screen.findByText("Rent");
    // 1500 + 4.5
    expect(screen.getByText("$1504.50")).toBeInTheDocument();
  });

  it("creates an expense through the modal", async () => {
    const user = userEvent.setup();
    const { container } = render(<Home />);
    await screen.findByText("Rent");

    await user.click(screen.getByRole("button", { name: /add expense/i }));
    expect(screen.getByText("New Expense")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("e.g. Electricity bill"), "Gym");
    await user.type(screen.getByPlaceholderText("0.00"), "50");
    // deadline (required date field)
    const dateInput = container.querySelector(
      'input[type="date"]',
    ) as HTMLInputElement;
    await user.type(dateInput, "2026-08-01");

    await user.click(screen.getByRole("button", { name: "Add Expense" }));

    await waitFor(() => expect(mocked.createExpense).toHaveBeenCalledTimes(1));
    const arg = mocked.createExpense.mock.calls[0][0];
    expect(arg.description).toBe("Gym");
    expect(arg.value).toBe(50);
    expect(arg.deadline).toBe("2026-08-01");
  });

  it("opens the edit modal pre-filled and updates", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    const editButtons = screen.getAllByRole("button", { name: /edit expense/i });
    await user.click(editButtons[0]);

    expect(screen.getByText("Edit Expense")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Rent")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() => expect(mocked.updateExpense).toHaveBeenCalledTimes(1));
    expect(mocked.updateExpense.mock.calls[0][0]).toBe("1");
  });

  it("deletes an expense after confirmation", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    const deleteButtons = screen.getAllByRole("button", {
      name: /delete expense/i,
    });
    await user.click(deleteButtons[0]);

    expect(screen.getByText("Delete Expense?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(mocked.deleteExpense).toHaveBeenCalledWith("1"));
  });

  it("cancels deletion without calling the API", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    await user.click(
      screen.getAllByRole("button", { name: /delete expense/i })[0],
    );
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByText("Delete Expense?")).not.toBeInTheDocument();
    expect(mocked.deleteExpense).not.toHaveBeenCalled();
  });

  it("surfaces an error when loading fails", async () => {
    mocked.listExpenses.mockRejectedValue(new Error("Backend down"));
    render(<Home />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend down");
  });
});
