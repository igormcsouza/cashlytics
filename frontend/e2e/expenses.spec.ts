import { readFileSync } from "node:fs";
import path from "node:path";
import { test, expect, type APIRequestContext } from "@playwright/test";

const API = process.env.E2E_API_BASE_URL ?? "http://localhost:5000";
const COGNITO_ENDPOINT =
  process.env.E2E_COGNITO_ENDPOINT ?? "http://localhost:9229";
const SHOTS = "e2e/screenshots";

// Deadlines are computed relative to "today" so the status colors are stable no
// matter when the suite runs.
function isoOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// `make up` writes the cognito-local client id here (see auth_bootstrap.py).
function readClientId(): string {
  const envPath = path.join(__dirname, "..", "..", "local", ".cognito.env");
  const match = readFileSync(envPath, "utf-8").match(
    /NEXT_PUBLIC_COGNITO_CLIENT_ID=(.+)/,
  );
  if (!match) {
    throw new Error(`NEXT_PUBLIC_COGNITO_CLIENT_ID not found in ${envPath}`);
  }
  return match[1].trim();
}

async function loginAsDevAdmin(): Promise<{
  idToken: string;
  refreshToken: string;
}> {
  const res = await fetch(COGNITO_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    },
    body: JSON.stringify({
      AuthFlow: "USER_PASSWORD_AUTH",
      ClientId: readClientId(),
      AuthParameters: { USERNAME: "admin@cashlytics.dev", PASSWORD: "password" },
    }),
  });
  const data = await res.json();
  return {
    idToken: data.AuthenticationResult.IdToken,
    refreshToken: data.AuthenticationResult.RefreshToken,
  };
}

async function resetExpenses(request: APIRequestContext, token: string) {
  const headers = { Authorization: `Bearer ${token}` };
  const existing = await (await request.get(`${API}/expenses`, { headers })).json();
  for (const e of existing) {
    await request.delete(`${API}/expenses/${e.id}`, { headers });
  }
}

async function seed(request: APIRequestContext, token: string) {
  const headers = { Authorization: `Bearer ${token}` };
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
    const res = await request.post(`${API}/expenses`, { data: f, headers });
    expect(res.ok()).toBeTruthy();
  }
}

test.beforeEach(async ({ request, page, baseURL }) => {
  const { idToken, refreshToken } = await loginAsDevAdmin();
  await resetExpenses(request, idToken);
  await seed(request, idToken);
  // Auth cookies the middleware/UI expect (mirrors lib/auth.ts's storeTokens).
  await page.context().addCookies([
    { name: "cashlytics_id_token", value: idToken, url: baseURL },
    { name: "cashlytics_refresh_token", value: refreshToken, url: baseURL },
  ]);
});

test("status colors, mark-as-paid, and total breakdown", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Internet (overdue)")).toBeVisible();

  const overdueRow = page.locator("tr", { hasText: "Internet (overdue)" });
  const dueTodayRow = page.locator("tr", { hasText: "Electricity (due today)" });
  const paidRow = page.locator("tr", { hasText: "Rent (paid)" });
  const upcomingRow = page.locator("tr", { hasText: "Gym (upcoming)" });

  await expect(overdueRow).toHaveClass(/bg-rose-500\/10/);
  await expect(dueTodayRow).toHaveClass(/bg-amber-500\/10/);
  await expect(paidRow).toHaveClass(/bg-emerald-500\/10/);
  await page.screenshot({ path: `${SHOTS}/table-status-colors.png`, fullPage: true });

  // Marking an unpaid expense paid turns its row green.
  await upcomingRow.getByRole("button", { name: "Mark as paid" }).click();
  await expect(
    page.locator("tr", { hasText: "Gym (upcoming)" }),
  ).toHaveClass(/bg-emerald-500\/10/);
  await page.screenshot({ path: `${SHOTS}/marked-paid.png`, fullPage: true });

  // Expanding the total card reveals the paid / not-due / due breakdown.
  await page.getByRole("button", { name: /toggle total breakdown/i }).click();
  await expect(page.getByText("Already paid")).toBeVisible();
  await expect(page.getByText("Remaining (not due)")).toBeVisible();
  await expect(page.getByText("Due", { exact: true })).toBeVisible();

  // Wait for the caret's rotate transition to settle before capturing.
  await page.waitForTimeout(300);
  await page.screenshot({
    path: `${SHOTS}/total-breakdown-expanded.png`,
    fullPage: true,
  });
});
