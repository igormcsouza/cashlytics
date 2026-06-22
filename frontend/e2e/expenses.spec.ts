import { test, expect, type APIRequestContext } from "@playwright/test";

const API = process.env.E2E_API_BASE_URL ?? "http://localhost:5000";
const SHOTS = "e2e/screenshots";

// Deadlines are computed relative to "today" so the status colors are stable no
// matter when the suite runs.
function isoOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

async function resetExpenses(request: APIRequestContext) {
  const existing = await (await request.get(`${API}/expenses`)).json();
  for (const e of existing) {
    await request.delete(`${API}/expenses/${e.id}`);
  }
}

async function seed(request: APIRequestContext) {
  const fixtures = [
    // Overdue -> red row
    { description: "Internet (overdue)", deadline: isoOffset(-7), value: 60, recurrent: true, paid: false },
    // Due today -> yellow row
    { description: "Electricity (due today)", deadline: isoOffset(0), value: 120.5, recurrent: true, paid: false },
    // Upcoming -> normal row; we'll mark this one paid in the UI
    { description: "Gym (upcoming)", deadline: isoOffset(20), value: 45, recurrent: false, paid: false },
    // Already paid -> green row
    { description: "Rent (paid)", deadline: isoOffset(10), value: 1500, recurrent: true, paid: true },
  ];
  for (const f of fixtures) {
    const res = await request.post(`${API}/expenses`, { data: f });
    expect(res.ok()).toBeTruthy();
  }
}

test.beforeEach(async ({ request }) => {
  await resetExpenses(request);
  await seed(request);
});

test("status colors, mark-as-paid, and total breakdown", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Internet (overdue)")).toBeVisible();

  const overdueRow = page.locator("tr", { hasText: "Internet (overdue)" });
  const dueTodayRow = page.locator("tr", { hasText: "Electricity (due today)" });
  const paidRow = page.locator("tr", { hasText: "Rent (paid)" });
  const upcomingRow = page.locator("tr", { hasText: "Gym (upcoming)" });

  // Soft status tints applied to the right rows.
  await expect(overdueRow).toHaveClass(/bg-rose-500\/10/);
  await expect(dueTodayRow).toHaveClass(/bg-amber-500\/10/);
  await expect(paidRow).toHaveClass(/bg-emerald-500\/10/);

  // Screenshot 1: the colored table.
  await page.screenshot({ path: `${SHOTS}/table-status-colors.png`, fullPage: true });

  // Mark the upcoming "Gym" expense as paid -> its row turns green.
  await upcomingRow.getByRole("button", { name: "Mark as paid" }).click();
  await expect(
    page.locator("tr", { hasText: "Gym (upcoming)" }),
  ).toHaveClass(/bg-emerald-500\/10/);

  // Screenshot 2: after marking paid.
  await page.screenshot({ path: `${SHOTS}/marked-paid.png`, fullPage: true });

  // Expand the total card and verify the breakdown appears.
  await page.getByRole("button", { name: /toggle total breakdown/i }).click();
  await expect(page.getByText("Already paid")).toBeVisible();
  await expect(page.getByText("Remaining (not due)")).toBeVisible();
  await expect(page.getByText("Due", { exact: true })).toBeVisible();

  // Screenshot 3: expanded breakdown.
  await page.screenshot({
    path: `${SHOTS}/total-breakdown-expanded.png`,
    fullPage: true,
  });
});
