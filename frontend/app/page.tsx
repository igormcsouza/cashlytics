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
import { authEnabled, getIdToken, logout } from "@/lib/auth";
import type { Expense, ExpenseInput } from "@/lib/types";
import { todayISO } from "@/lib/status";

export default function Home() {
  // Middleware only checks that an auth cookie exists, not that it's still
  // valid, so a stale/expired session can slip through to this page. Hold off
  // rendering real content until we've actually resolved a usable token (or
  // given up and sent the browser to /login) — otherwise the table flashes
  // for a moment before the redirect lands.
  const [checkingAuth, setCheckingAuth] = useState(authEnabled);

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
    if (!authEnabled) {
      refresh();
      return;
    }
    (async () => {
      const token = await getIdToken();
      if (!token) {
        window.location.href = "/login";
        return;
      }
      setCheckingAuth(false);
      await refresh();
    })();
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

  function handleLogout() {
    logout();
    window.location.href = "/login";
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

  if (checkingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex gap-2" role="status" aria-label="Loading">
          <span className="w-3 h-3 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.3s]" />
          <span className="w-3 h-3 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]" />
          <span className="w-3 h-3 rounded-full bg-indigo-400 animate-bounce" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-indigo-300">💰 Cashlytics</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={openCreate}
            className="bg-indigo-500 hover:bg-indigo-400 text-white font-semibold px-4 py-2 rounded-lg shadow-lg shadow-indigo-950/40 flex items-center gap-2"
          >
            <span className="text-xl leading-none">+</span> Add Expense
          </button>
          {authEnabled && (
            <button
              onClick={handleLogout}
              aria-label="Log out"
              title="Log out"
              className="bg-indigo-500 hover:bg-indigo-400 text-white p-2.5 rounded-lg shadow-lg shadow-indigo-950/40"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="w-5 h-5"
                aria-hidden="true"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          )}
        </div>
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
                "inline-block text-indigo-300 transition-transform duration-200 " +
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
