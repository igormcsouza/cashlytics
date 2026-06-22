import type { Expense } from "./types";

// The visual state of an expense row, in priority order: a paid expense is
// always "paid" regardless of its deadline; otherwise urgency is derived from
// the deadline relative to today.
export type ExpenseStatus = "paid" | "overdue" | "due-today" | "upcoming";

/** Today's local date as a `YYYY-MM-DD` string, comparable to a deadline. */
export function todayISO(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Classify an expense for display. Deadlines are `YYYY-MM-DD` strings, which
 * compare correctly with lexicographic string comparison.
 */
export function expenseStatus(
  expense: Expense,
  today: string = todayISO(),
): ExpenseStatus {
  if (expense.paid) return "paid";
  if (expense.deadline < today) return "overdue";
  if (expense.deadline === today) return "due-today";
  return "upcoming";
}
