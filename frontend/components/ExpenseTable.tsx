import { Check, Pencil, Trash2, Undo2 } from "lucide-react";
import type { Expense } from "@/lib/types";
import { expenseStatus } from "@/lib/status";

interface Props {
  expenses: Expense[];
  loading?: boolean;
  onEdit: (expense: Expense) => void;
  onDelete: (expense: Expense) => void;
  onTogglePaid: (expense: Expense) => void;
}

// Soft, low-opacity row tints per status so the table stays easy on the eyes.
const ROW_CLASS: Record<string, string> = {
  paid: "bg-emerald-500/10 hover:bg-emerald-500/15",
  overdue: "bg-rose-500/10 hover:bg-rose-500/15",
  "due-today": "bg-amber-500/10 hover:bg-amber-500/15",
  upcoming: "hover:bg-slate-800/70",
};

export default function ExpenseTable({
  expenses,
  loading = false,
  onEdit,
  onDelete,
  onTogglePaid,
}: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl shadow-black/20 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-800 text-indigo-200 uppercase text-xs font-semibold">
          <tr>
            <th className="px-4 py-3 text-center">Description</th>
            <th className="px-4 py-3 text-center">Deadline</th>
            <th className="px-4 py-3 text-center">Value</th>
            <th className="px-4 py-3 text-center">Recurrent</th>
            <th className="px-4 py-3 text-center">Installments</th>
            <th className="px-4 py-3 text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="px-4 py-10 text-center">
                <div
                  role="status"
                  aria-label="Loading expenses"
                  className="flex items-center justify-center gap-3 text-slate-400"
                >
                  <div className="flex gap-2">
                    <span className="w-3 h-3 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-3 h-3 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-3 h-3 rounded-full bg-indigo-400 animate-bounce" />
                  </div>
                  <span>Loading expenses…</span>
                </div>
              </td>
            </tr>
          ) : expenses.length === 0 ? (
            <tr>
              <td
                colSpan={6}
                className="px-4 py-6 text-center text-slate-500"
              >
                No expenses yet. Click &quot;Add Expense&quot; to get started.
              </td>
            </tr>
          ) : (
            expenses.map((expense) => (
              <tr
                key={expense.id}
                onDoubleClick={() => onEdit(expense)}
                className={
                  "border-t border-slate-800 transition " +
                  ROW_CLASS[expenseStatus(expense)]
                }
              >
                <td className="px-4 py-3 text-center">{expense.description}</td>
                <td className="px-4 py-3 text-center">{expense.deadline}</td>
                <td className="px-4 py-3 text-center">
                  ${expense.value.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={
                      "px-2 py-0.5 rounded-full text-xs font-medium " +
                      (expense.recurrent
                        ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/25"
                        : "bg-slate-800 text-slate-300 ring-1 ring-slate-700")
                    }
                  >
                    {expense.recurrent ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  {expense.installment_total
                    ? `${expense.installment_current} / ${expense.installment_total}`
                    : "—"}
                </td>
                <td
                  className="px-4 py-3 text-center"
                  onDoubleClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-center gap-1.5 sm:gap-2">
                    <button
                      onClick={() => onTogglePaid(expense)}
                      className={
                        "inline-flex h-8 w-8 items-center justify-center text-white rounded text-sm font-medium " +
                        (expense.paid
                          ? "bg-slate-600 hover:bg-slate-500"
                          : "bg-emerald-600 hover:bg-emerald-500")
                      }
                      title={expense.paid ? "Mark as unpaid" : "Mark as paid"}
                      aria-label={
                        expense.paid ? "Mark as unpaid" : "Mark as paid"
                      }
                    >
                      {expense.paid ? (
                        <Undo2 className="h-4 w-4" aria-hidden="true" />
                      ) : (
                        <Check className="h-4 w-4" aria-hidden="true" />
                      )}
                    </button>
                    <button
                      onClick={() => onEdit(expense)}
                      className="inline-flex h-8 w-8 items-center justify-center bg-blue-700 hover:bg-blue-600 text-white rounded text-sm font-medium"
                      title="Edit"
                      aria-label="Edit expense"
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      onClick={() => onDelete(expense)}
                      className="inline-flex h-8 w-8 items-center justify-center bg-red-600 hover:bg-red-500 text-white rounded text-sm font-medium"
                      title="Delete"
                      aria-label="Delete expense"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
