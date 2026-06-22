"use client";

import { useEffect, useMemo, useState } from "react";
import DeleteConfirm from "@/components/DeleteConfirm";
import ExpenseModal from "@/components/ExpenseModal";
import ExpenseTable from "@/components/ExpenseTable";
import {
  createExpense,
  deleteExpense,
  listExpenses,
  updateExpense,
} from "@/lib/api";
import type { Expense, ExpenseInput } from "@/lib/types";
import { todayISO } from "@/lib/status";

export default function Home() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);

  const [deleting, setDeleting] = useState<Expense | null>(null);

  const [showBreakdown, setShowBreakdown] = useState(false);

  const total = useMemo(
    () => expenses.reduce((sum, e) => sum + e.value, 0),
    [expenses],
  );

  // Breakdown of the total: already paid, still upcoming (not yet due), and due
  // (unpaid and on/past the deadline).
  const { totalPaid, totalNotDue, totalDue } = useMemo(() => {
    const today = todayISO();
    let totalPaid = 0;
    let totalNotDue = 0;
    let totalDue = 0;
    for (const e of expenses) {
      if (e.paid) totalPaid += e.value;
      else if (e.deadline > today) totalNotDue += e.value;
      else totalDue += e.value;
    }
    return { totalPaid, totalNotDue, totalDue };
  }, [expenses]);

  async function refresh() {
    try {
      setExpenses(await listExpenses());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load expenses.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function openCreate() {
    setEditing(null);
    setShowModal(true);
  }

  function openEdit(expense: Expense) {
    setEditing(expense);
    setShowModal(true);
  }

  async function handleSubmit(input: ExpenseInput) {
    try {
      if (editing) {
        await updateExpense(editing.id, input);
      } else {
        await createExpense(input);
      }
      setShowModal(false);
      setError(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "An error occurred.");
    }
  }

  async function handleTogglePaid(expense: Expense) {
    try {
      const { description, deadline, value, recurrent } = expense;
      await updateExpense(expense.id, {
        description,
        deadline,
        value,
        recurrent,
        paid: !expense.paid,
      });
      setError(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update expense.");
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    try {
      await deleteExpense(deleting.id);
      setDeleting(null);
      setError(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete expense.");
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-indigo-300">💰 Cashlytics</h1>
        <button
          onClick={openCreate}
          className="bg-indigo-500 hover:bg-indigo-400 text-white font-semibold px-4 py-2 rounded-lg shadow-lg shadow-indigo-950/40 flex items-center gap-2"
        >
          <span className="text-xl leading-none">+</span> Add Expense
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="bg-red-500/15 text-red-300 ring-1 ring-red-500/25 rounded-lg px-4 py-3 mb-6"
        >
          {error}
        </div>
      )}

      {/* Total */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl shadow-black/20 mb-6">
        <button
          type="button"
          onClick={() => setShowBreakdown((v) => !v)}
          aria-expanded={showBreakdown}
          aria-label="Toggle total breakdown"
          className="w-full p-4 flex items-center justify-between text-left"
        >
          <span className="flex items-center gap-2 text-slate-300 font-medium">
            <span
              className={
                "text-indigo-300 transition-transform " +
                (showBreakdown ? "rotate-90" : "")
              }
            >
              ▶
            </span>
            Total Expenses
          </span>
          <span className="text-2xl font-bold text-indigo-300">
            ${total.toFixed(2)}
          </span>
        </button>

        {showBreakdown && (
          <div className="border-t border-slate-800 px-4 py-3 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-emerald-300">Already paid</span>
              <span className="font-semibold text-emerald-300">
                ${totalPaid.toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Remaining (not due)</span>
              <span className="font-semibold text-slate-200">
                ${totalNotDue.toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-rose-300">Due</span>
              <span className="font-semibold text-rose-300">
                ${totalDue.toFixed(2)}
              </span>
            </div>
          </div>
        )}
      </div>

      <ExpenseTable
        expenses={expenses}
        onEdit={openEdit}
        onDelete={setDeleting}
        onTogglePaid={handleTogglePaid}
      />

      <ExpenseModal
        open={showModal}
        editing={editing}
        onSubmit={handleSubmit}
        onClose={() => setShowModal(false)}
      />

      <DeleteConfirm
        open={deleting !== null}
        expense={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
