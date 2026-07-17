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
            <th className="px-4 py-3 text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={5} className="px-4 py-10 text-center">
                <div
                  role="status"
                  aria-label="Loading expenses"
                  className="flex items-center justify-center gap-3 text-slate-400"
                >
                  <svg
                    className="h-5 w-5 animate-spin text-indigo-400"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  <span>Loading expenses…</span>
                </div>
              </td>
            </tr>
          ) : expenses.length === 0 ? (
            <tr>
              <td
                colSpan={5}
                className="px-4 py-6 text-center text-slate-500"
              >
                No expenses yet. Click &quot;Add Expense&quot; to get started.
              </td>
            </tr>
          ) : (
            expenses.map((expense) => (
              <tr
                key={expense.id}
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
                <td className="px-4 py-3 text-center space-x-2">
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
                    {expense.paid ? "↩️" : "✅"}
                  </button>
                  <button
                    onClick={() => onEdit(expense)}
                    className="inline-flex h-8 w-8 items-center justify-center bg-blue-700 hover:bg-blue-600 text-white rounded text-sm font-medium"
                    title="Edit"
                    aria-label="Edit expense"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => onDelete(expense)}
                    className="inline-flex h-8 w-8 items-center justify-center bg-red-600 hover:bg-red-500 text-white rounded text-sm font-medium"
                    title="Delete"
                    aria-label="Delete expense"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
