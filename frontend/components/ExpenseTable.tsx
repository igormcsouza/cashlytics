import type { Expense } from "@/lib/types";

interface Props {
  expenses: Expense[];
  onEdit: (expense: Expense) => void;
  onDelete: (expense: Expense) => void;
}

export default function ExpenseTable({ expenses, onEdit, onDelete }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl shadow-black/20 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-800 text-indigo-200 uppercase text-xs font-semibold">
          <tr>
            <th className="px-4 py-3 text-left">Description</th>
            <th className="px-4 py-3 text-left">Deadline</th>
            <th className="px-4 py-3 text-right">Value</th>
            <th className="px-4 py-3 text-center">Recurrent</th>
            <th className="px-4 py-3 text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {expenses.length === 0 ? (
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
                className="border-t border-slate-800 hover:bg-slate-800/70 transition"
              >
                <td className="px-4 py-3">{expense.description}</td>
                <td className="px-4 py-3">{expense.deadline}</td>
                <td className="px-4 py-3 text-right">
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
