import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
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
    deadline: "2000-01-01",
    value: 1500,
    recurrent: true,
    paid: false,
    category: "Housing",
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

const INSTALLMENT_EXPENSE: Expense = {
  id: "3",
  description: "TV",
  deadline: "2026-07-10",
  value: 300,
  recurrent: false,
  paid: false,
  installment_current: 2,
  installment_total: 5,
};

beforeEach(() => {
  vi.clearAllMocks();
  mocked.listExpenses.mockResolvedValue([...EXPENSES]);
  mocked.createExpense.mockResolvedValue(EXPENSES[0]);
  mocked.updateExpense.mockResolvedValue(EXPENSES[0]);
  mocked.deleteExpense.mockResolvedValue();
  mocked.setExpensePaid.mockResolvedValue({ ...EXPENSES[0], paid: true });
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

    // Scoped to the modal form: the header "Add Expense" button now shares
    // the same accessible name (via aria-label) as this submit button.
    const submitButton = container.querySelector(
      'form button[type="submit"]',
    ) as HTMLButtonElement;
    expect(submitButton).toHaveTextContent("Add Expense");
    await user.click(submitButton);

    await waitFor(() => expect(mocked.createExpense).toHaveBeenCalledTimes(1));
    const arg = mocked.createExpense.mock.calls[0][0];
    expect(arg.description).toBe("Gym");
    expect(arg.value).toBe(50);
    expect(arg.deadline).toBe("2026-08-01");
  });

  it("shows the compact '+ Expense' label on the header button at all widths", async () => {
    render(<Home />);
    await screen.findByText("Rent");

    // aria-label keeps the accessible name as "Add Expense" even though the
    // visible label is shortened to "Expense".
    const addButton = screen.getByRole("button", { name: "Add Expense" });
    const label = addButton.querySelector("span:last-child");
    expect(label).toHaveTextContent("Expense");
    expect(label?.className ?? "").not.toContain("hidden");
  });

  it("renders the category select with all options", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    await user.click(screen.getByRole("button", { name: /add expense/i }));

    const select = screen.getByLabelText("Category") as HTMLSelectElement;
    const optionLabels = Array.from(select.options).map((o) => o.textContent);
    expect(optionLabels).toEqual([
      "Uncategorized",
      "Housing",
      "Leisure",
      "Food",
      "Transport",
      "Health",
      "Other",
    ]);
  });

  it("selects a category and sends it when creating an expense", async () => {
    const user = userEvent.setup();
    const { container } = render(<Home />);
    await screen.findByText("Rent");

    await user.click(screen.getByRole("button", { name: /add expense/i }));

    await user.type(screen.getByPlaceholderText("e.g. Electricity bill"), "Groceries");
    await user.type(screen.getByPlaceholderText("0.00"), "25");
    const dateInput = container.querySelector(
      'input[type="date"]',
    ) as HTMLInputElement;
    await user.type(dateInput, "2026-08-01");
    await user.selectOptions(screen.getByLabelText("Category"), "Food");

    // Scoped to the modal form: the header "Add Expense" button now shares
    // the same accessible name (via aria-label) as this submit button.
    const submitButton = container.querySelector(
      'form button[type="submit"]',
    ) as HTMLButtonElement;
    await user.click(submitButton);

    await waitFor(() => expect(mocked.createExpense).toHaveBeenCalledTimes(1));
    expect(mocked.createExpense.mock.calls[0][0].category).toBe("Food");
  });

  it("opens the edit modal pre-filled and updates", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    const editButtons = screen.getAllByRole("button", { name: /edit expense/i });
    await user.click(editButtons[0]);

    expect(screen.getByText("Edit Expense")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Rent")).toBeInTheDocument();
    expect(
      (screen.getByLabelText("Category") as HTMLSelectElement).value,
    ).toBe("Housing");

    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() => expect(mocked.updateExpense).toHaveBeenCalledTimes(1));
    expect(mocked.updateExpense.mock.calls[0][0]).toBe("1");
  });

  it("opens the edit modal pre-filled when a row is double-clicked", async () => {
    render(<Home />);
    const rentRow = (await screen.findByText("Rent")).closest("tr") as HTMLElement;

    fireEvent.doubleClick(rentRow);

    expect(screen.getByText("Edit Expense")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Rent")).toBeInTheDocument();
  });

  it("opens the modal with an installment expense pre-filled", async () => {
    const user = userEvent.setup();
    mocked.listExpenses.mockResolvedValue([...EXPENSES, INSTALLMENT_EXPENSE]);
    render(<Home />);
    await screen.findByText("TV");

    const editButtons = screen.getAllByRole("button", { name: /edit expense/i });
    // Rent, Coffee, TV -> TV is the third row.
    await user.click(editButtons[2]);

    expect(screen.getByText("Edit Expense")).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: /has installments/i }),
    ).toBeChecked();
    expect(screen.getByDisplayValue("2")).toBeInTheDocument();
    expect(screen.getByDisplayValue("5")).toBeInTheDocument();
  });

  it("toggling off installments and submitting sends nulls", async () => {
    const user = userEvent.setup();
    mocked.listExpenses.mockResolvedValue([...EXPENSES, INSTALLMENT_EXPENSE]);
    render(<Home />);
    await screen.findByText("TV");

    const editButtons = screen.getAllByRole("button", { name: /edit expense/i });
    await user.click(editButtons[2]);

    await user.click(
      screen.getByRole("checkbox", { name: /has installments/i }),
    );
    await user.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(mocked.updateExpense).toHaveBeenCalledTimes(1));
    const arg = mocked.updateExpense.mock.calls[0][1];
    expect(arg.installment_current).toBeNull();
    expect(arg.installment_total).toBeNull();
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

  it("marks an expense as paid for the currently viewed month only", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    // Rent (id "1") is unpaid -> button is "Mark as paid".
    const payButtons = screen.getAllByRole("button", { name: "Mark as paid" });
    await user.click(payButtons[0]);

    await waitFor(() =>
      expect(mocked.setExpensePaid).toHaveBeenCalledTimes(1),
    );
    const [id, month, paid] = mocked.setExpensePaid.mock.calls[0];
    expect(id).toBe("1");
    expect(month).toMatch(/^\d{4}-\d{2}$/);
    expect(paid).toBe(true);
  });

  it("colors rows by status (overdue red, paid green)", async () => {
    render(<Home />);
    const rentRow = (await screen.findByText("Rent")).closest("tr");
    const coffeeRow = screen.getByText("Coffee").closest("tr");
    // Rent is unpaid and past its deadline -> rose; Coffee is paid -> emerald.
    expect(rentRow?.className).toContain("bg-rose-500/10");
    expect(coffeeRow?.className).toContain("bg-emerald-500/10");
  });

  it("expands the total card to show the breakdown", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    expect(screen.queryByText("Already paid")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /toggle total breakdown/i }),
    );

    const paidRow = screen.getByText("Already paid").closest("div");
    const dueRow = screen.getByText("Due").closest("div");
    expect(screen.getByText("Remaining (not due)")).toBeInTheDocument();
    // Coffee (4.50) is paid; Rent (1500) is overdue and unpaid.
    expect(paidRow).toHaveTextContent("$4.50");
    expect(dueRow).toHaveTextContent("$1500.00");
  });

  it("surfaces an error when loading fails", async () => {
    mocked.listExpenses.mockRejectedValue(new Error("Backend down"));
    render(<Home />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend down");
  });

  it("fetches the current month on load and navigates via the arrows", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Rent");

    expect(mocked.listExpenses).toHaveBeenCalledTimes(1);
    const initialMonth = mocked.listExpenses.mock.calls[0][0];
    expect(initialMonth).toMatch(/^\d{4}-\d{2}$/);

    await user.click(screen.getByRole("button", { name: "Previous month" }));
    await waitFor(() =>
      expect(mocked.listExpenses).toHaveBeenCalledTimes(2),
    );
    expect(mocked.listExpenses.mock.calls[1][0]).not.toBe(initialMonth);

    await user.click(screen.getByRole("button", { name: "Next month" }));
    await user.click(screen.getByRole("button", { name: "Next month" }));
    await waitFor(() =>
      expect(mocked.listExpenses).toHaveBeenCalledTimes(4),
    );
    // Back to the original month, then one past it.
    expect(mocked.listExpenses.mock.calls[3][0]).not.toBe(initialMonth);
  });
});
