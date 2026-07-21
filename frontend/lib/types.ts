export interface Expense {
  id: string;
  description: string;
  deadline: string;
  value: number;
  recurrent: boolean;
  paid: boolean;
  installment_current?: number | null;
  installment_total?: number | null;
}

export type ExpenseInput = Omit<Expense, "id">;
