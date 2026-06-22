export interface Expense {
  id: string;
  description: string;
  deadline: string;
  value: number;
  recurrent: boolean;
  paid: boolean;
}

export type ExpenseInput = Omit<Expense, "id">;
