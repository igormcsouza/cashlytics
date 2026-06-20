export interface Expense {
  id: string;
  description: string;
  deadline: string;
  value: number;
  recurrent: boolean;
}

export type ExpenseInput = Omit<Expense, "id">;
