import { describe, expect, it } from "vitest";
import { expenseStatus } from "@/lib/status";
import type { Expense } from "@/lib/types";

const TODAY = "2026-06-22";

function make(overrides: Partial<Expense>): Expense {
  return {
    id: "x",
    description: "Test",
    deadline: TODAY,
    value: 10,
    recurrent: false,
    paid: false,
    ...overrides,
  };
}

describe("expenseStatus", () => {
  it("is 'paid' regardless of deadline when paid", () => {
    expect(expenseStatus(make({ paid: true, deadline: "2000-01-01" }), TODAY)).toBe(
      "paid",
    );
  });

  it("is 'overdue' when unpaid and deadline is in the past", () => {
    expect(expenseStatus(make({ deadline: "2026-06-21" }), TODAY)).toBe("overdue");
  });

  it("is 'due-today' when unpaid and deadline is today", () => {
    expect(expenseStatus(make({ deadline: TODAY }), TODAY)).toBe("due-today");
  });

  it("is 'upcoming' when unpaid and deadline is in the future", () => {
    expect(expenseStatus(make({ deadline: "2026-06-23" }), TODAY)).toBe("upcoming");
  });
});
