// Helpers for the month-navigation UI (issue #10). Months are represented as
// `YYYY-MM` strings, comparable lexicographically like `deadline` dates.

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** The current local month as a `YYYY-MM` string. */
export function currentYearMonth(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

/** Shift a `YYYY-MM` string by `delta` months (may be negative). */
export function shiftMonth(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const total = year * 12 + (mon - 1) + delta;
  const newYear = Math.floor(total / 12);
  const newMonth = ((total % 12) + 12) % 12;
  return `${newYear}-${String(newMonth + 1).padStart(2, "0")}`;
}

/** Human-readable label for a `YYYY-MM` string, e.g. "July 2026". */
export function formatMonthLabel(month: string): string {
  const [year, mon] = month.split("-").map(Number);
  return `${MONTH_NAMES[mon - 1]} ${year}`;
}
