import { useEffect, useState } from "react";
import type { Expense, ExpenseInput } from "@/lib/types";

interface Props {
  open: boolean;
  editing: Expense | null;
  onSubmit: (input: ExpenseInput) => void;
  onClose: () => void;
}

const EMPTY: ExpenseInput = {
  description: "",
  deadline: "",
  value: 0,
  recurrent: false,
};

export default function ExpenseModal({
  open,
  editing,
  onSubmit,
  onClose,
}: Props) {
  const [form, setForm] = useState<ExpenseInput>(EMPTY);

  useEffect(() => {
    if (editing) {
      const { description, deadline, value, recurrent } = editing;
      setForm({ description, deadline, value, recurrent });
    } else {
      setForm(EMPTY);
    }
  }, [editing, open]);

  if (!open) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl shadow-black/50 p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-bold text-indigo-300 mb-4">
          {editing ? "Edit Expense" : "New Expense"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Description
            </label>
            <input
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              type="text"
              required
              className="w-full bg-slate-950 border border-slate-700 text-slate-100 placeholder:text-slate-500 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400"
              placeholder="e.g. Electricity bill"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Deadline
            </label>
            <input
              value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              type="date"
              required
              className="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Value ($)
            </label>
            <input
              value={form.value}
              onChange={(e) =>
                setForm({ ...form, value: parseFloat(e.target.value) || 0 })
              }
              type="number"
              step="0.01"
              min="0"
              required
              className="w-full bg-slate-950 border border-slate-700 text-slate-100 placeholder:text-slate-500 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400"
              placeholder="0.00"
            />
          </div>
          <div className="flex items-center gap-3">
            <input
              checked={form.recurrent}
              onChange={(e) =>
                setForm({ ...form, recurrent: e.target.checked })
              }
              id="recurrent"
              type="checkbox"
              className="w-4 h-4 accent-indigo-500"
            />
            <label
              htmlFor="recurrent"
              className="text-sm font-medium text-slate-300"
            >
              Recurrent expense
            </label>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              className="flex-1 bg-indigo-500 hover:bg-indigo-400 text-white font-semibold py-2 rounded-lg"
            >
              {editing ? "Save Changes" : "Add Expense"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2 rounded-lg"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
