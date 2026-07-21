export const EXPENSE_CATEGORIES = [
  "Housing",
  "Leisure",
  "Food",
  "Transport",
  "Health",
  "Other",
] as const;

export type ExpenseCategory = (typeof EXPENSE_CATEGORIES)[number];

export interface Expense {
  id: string;
  description: string;
  deadline: string;
  value: number;
  recurrent: boolean;
  paid: boolean;
  category?: ExpenseCategory | null;
  installment_current?: number | null;
  installment_total?: number | null;
}

export type ExpenseInput = Omit<Expense, "id">;
