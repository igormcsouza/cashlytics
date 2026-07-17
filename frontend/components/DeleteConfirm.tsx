import { Trash2 } from "lucide-react";
import type { Expense } from "@/lib/types";

interface Props {
  open: boolean;
  expense: Expense | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function DeleteConfirm({
  open,
  expense,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl shadow-black/50 p-6 w-full max-w-sm mx-4 text-center">
        <div className="flex justify-center mb-3 text-red-500">
          <Trash2 className="h-10 w-10" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Delete Expense?</h2>
        <p className="text-slate-400 mb-6">
          Are you sure you want to delete{" "}
          <strong>{expense?.description}</strong>? This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onConfirm}
            className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-2 rounded-lg"
          >
            Delete
          </button>
          <button
            onClick={onCancel}
            className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2 rounded-lg"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
