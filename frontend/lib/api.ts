import { authEnabled, getIdToken, logout } from "./auth";
import type { Expense, ExpenseInput } from "./types";

// API base URL is configured per environment: the local backend in dev and the
// Lambda/API Gateway URL in production. Falls back to a relative path.
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function url(path: string): string {
  return `${BASE_URL}${path}`;
}

// Attaches the Cognito id token (silently refreshed when expired); a 401 means
// the session is gone for good, so drop the cookies and go to the login page.
async function authFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (authEnabled) {
    const token = await getIdToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(input, { ...init, headers });
  if (res.status === 401 && authEnabled && typeof window !== "undefined") {
    logout();
    window.location.href = "/login";
  }
  return res;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.detail ?? data.error ?? "An error occurred. Please try again.";
  } catch {
    return "An error occurred. Please try again.";
  }
}

export async function listExpenses(): Promise<Expense[]> {
  const res = await authFetch(url("/expenses"));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createExpense(input: ExpenseInput): Promise<Expense> {
  const res = await authFetch(url("/expenses"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function updateExpense(
  id: string,
  input: ExpenseInput,
): Promise<Expense> {
  const res = await authFetch(url(`/expenses/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteExpense(id: string): Promise<void> {
  const res = await authFetch(url(`/expenses/${id}`), { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    throw new Error("Failed to delete expense. Please try again.");
  }
}
